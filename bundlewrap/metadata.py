from copy import copy
from hashlib import sha1
from json import dumps, JSONEncoder

from .exceptions import RepositoryError
from .utils import Fault
from .utils.dicts import ATOMIC_TYPES, map_dict_keys, merge_dict, value_at_key_path
from .utils.text import force_text, mark_for_translation as _


METADATA_TYPES = (  # only meant for natively atomic types
    bool,
    bytes,
    Fault,
    int,
    str,
    type(None),
)


class DoNotRunAgain(Exception):
    """
    Raised from metadata reactors to indicate they can be disregarded.
    """
    pass


def deepcopy_metadata(obj):
    """
    Our own version of deepcopy.copy that doesn't pickle.
    """
    if isinstance(obj, METADATA_TYPES):
        return obj
    elif isinstance(obj, dict):
        if isinstance(obj, ATOMIC_TYPES[dict]):
            new_obj = atomic({})
        else:
            new_obj = {}
        for key, value in obj.items():
            new_key = copy(key)
            new_obj[new_key] = deepcopy_metadata(value)
    elif isinstance(obj, (list, tuple)):
        if isinstance(obj, (ATOMIC_TYPES[list], ATOMIC_TYPES[tuple])):
            new_obj = atomic([])
        else:
            new_obj = []
        for member in obj:
            new_obj.append(deepcopy_metadata(member))
    elif isinstance(obj, set):
        if isinstance(obj, ATOMIC_TYPES[set]):
            new_obj = atomic(set())
        else:
            new_obj = set()
        for member in obj:
            new_obj.add(deepcopy_metadata(member))
    else:
        assert False  # there should be no other types
    return new_obj


def validate_metadata(metadata, _top_level=True):
    if _top_level and not isinstance(metadata, dict):
        raise TypeError(_("metadata must be a dict"))
    if isinstance(metadata, dict):
        for key, value in metadata.items():
            if not isinstance(key, str):
                raise TypeError(_("metadata keys must be str: {value} is {type}").format(
                    type=type(key),
                    value=repr(key),
                ))
            validate_metadata(value, _top_level=False)
    elif isinstance(metadata, (tuple, list, set)):
        for value in metadata:
            validate_metadata(value, _top_level=False)
    elif not isinstance(metadata, METADATA_TYPES):
        raise TypeError(_("illegal metadata value type: {value} is {type}").format(
            type=type(metadata),
            value=repr(metadata),
        ))


def atomic(obj):
    """
    Wraps a compatible object in a custom class to prevent it from being
    merged with another object of the same type during metadata
    compilation.
    """
    try:
        cls = ATOMIC_TYPES[type(obj)]
    except KeyError:
        raise ValueError("atomic() can only be applied to dicts, lists, sets, or tuples "
                         "(not: {})".format(repr(obj)))
    else:
        return cls(obj)


def check_for_metadata_conflicts(node):
    check_for_metadata_conflicts_between_groups(node)
    check_for_metadata_conflicts_between_defaults_and_reactors(node)


def check_for_metadata_conflicts_between_defaults_and_reactors(node):
    """
    Finds conflicting metadata keys in bundle defaults and reactors.

    Dicts can be merged with dicts, sets can be merged with sets, but
    any other combination is a conflict.
    """
    TYPE_DICT = 1
    TYPE_SET = 2
    TYPE_OTHER = 3

    def paths_with_values_and_types(d):
        for path in map_dict_keys(d):
            value = value_at_key_path(d, path)
            if isinstance(value, dict):
                yield path, value, TYPE_DICT
            elif isinstance(value, set):
                yield path, value, TYPE_SET
            else:
                yield path, value, TYPE_OTHER

    for prefix in ("metadata_defaults:", "metadata_reactor:"):
        paths = {}
        node.metadata.get(tuple())  # ensure full metadata is present
        for partition in node.metadata.stack._partitions:
            for identifier, layer in partition.items():
                if identifier.startswith(prefix):
                    for path, value, current_type in paths_with_values_and_types(layer):
                        try:
                            prev_type, prev_identifier, prev_value = paths[path]
                        except KeyError:
                            paths[path] = current_type, identifier, value
                        else:
                            if (
                                prev_type == TYPE_DICT
                                and current_type == TYPE_DICT
                            ):
                                pass
                            elif (
                                prev_type == TYPE_SET
                                and current_type == TYPE_SET
                            ):
                                pass
                            elif value != prev_value:
                                raise ValueError(_(
                                    "{node}: {a} and {b} are clashing over this key path: {path} "
                                    "({val_a} vs. {val_b})"
                                ).format(
                                    a=identifier,
                                    b=prev_identifier,
                                    node=node.name,
                                    path="/".join(path),
                                    val_a=repr(value),
                                    val_b=repr(prev_value),
                                ))


def check_for_metadata_conflicts_between_groups(node):
    """
    Finds metadata keys defined by two groups that are not part of a
    shared subgroup hierarchy.
    """
    # First, we build a list of subgroup chains.
    #
    # A chain is simply a list of groups starting with a parent group
    # that has no parent groups itself and then descends depth-first
    # into its subgroups until a subgroup is reached that the node is
    # not a member of.
    # Every possible path on every subgroup tree is a separate chain.
    #
    #      group4
    #     /     \
    #  group2  group3
    #     \     /
    #     group1
    #
    # This example has two chains, even though both start and end at the
    # some groups:
    #
    #     group1 -> group2 -> group4
    #     group1 -> group3 -> group4
    #

    # find all groups whose subgroups this node is *not* a member of
    lowest_subgroups = set()
    for group in node.groups:
        in_subgroup = False
        for subgroup in group.subgroups:
            if subgroup in node.groups:
                in_subgroup = True
                break
        if not in_subgroup:
            lowest_subgroups.add(group)

    chains = []
    incomplete_chains = [[group] for group in lowest_subgroups]

    while incomplete_chains:
        for chain in incomplete_chains[:]:
            highest_group = chain[-1]
            if list(highest_group.parent_groups):
                chain_so_far = chain[:]
                # continue this chain with the first parent group
                chain.append(list(highest_group.parent_groups)[0])
                # further parent groups form new chains
                for further_parents in list(highest_group.parent_groups)[1:]:
                    new_chain = chain_so_far[:]
                    new_chain.append(further_parents)
                    incomplete_chains.append(new_chain)
            else:
                # chain has ended
                chains.append(chain)
                incomplete_chains.remove(chain)

    # chains now look like this (parents right of children):
    # [
    #     [group1],
    #     [group2, group3, group5],
    #     [group2, group4, group5],
    #     [group2, group4, group6, group7],
    # ]

    # let's merge metadata for each chain
    chain_metadata = []
    for chain in chains:
        metadata = {}
        for group in chain:
            metadata = merge_dict(metadata, group._attributes.get('metadata', {}))
        chain_metadata.append(metadata)

    # create a "key path map" for each chain's metadata
    chain_metadata_keys = [list(map_dict_keys(metadata)) for metadata in chain_metadata]

    # compare all metadata keys with other chains and find matches
    for index1, keymap1 in enumerate(chain_metadata_keys):
        for keypath in keymap1:
            for index2, keymap2 in enumerate(chain_metadata_keys):
                if index1 == index2:
                    # same keymap, don't compare
                    continue
                else:
                    if keypath in keymap2:
                        if (
                            type(value_at_key_path(chain_metadata[index1], keypath)) ==
                            type(value_at_key_path(chain_metadata[index2], keypath)) and
                            type(value_at_key_path(chain_metadata[index2], keypath)) in
                            (set, dict)
                        ):
                            continue
                        # We now know that there is a conflict between the first
                        # and second chain we're looking at right now.
                        # That is however not a problem if the conflict is caused
                        # by a group that is present in both chains.
                        # So all that's left is to figure out which two single groups
                        # within those chains are at fault so we can report them
                        # to the user if necessary.
                        find_groups_causing_metadata_conflict(
                            node.name,
                            chains[index1],
                            chains[index2],
                            keypath,
                        )


def find_groups_causing_metadata_conflict(node_name, chain1, chain2, keypath):
    """
    Given two chains (lists of groups), find one group in each chain
    that has conflicting metadata with the other for the given key path.
    """
    chain1_metadata = [
        list(map_dict_keys(group._attributes.get('metadata', {}))) for group in chain1
    ]
    chain2_metadata = [
        list(map_dict_keys(group._attributes.get('metadata', {}))) for group in chain2
    ]

    bad_keypath = None

    for index1, keymap1 in enumerate(chain1_metadata):
        for index2, keymap2 in enumerate(chain2_metadata):
            if chain1[index1] == chain2[index2]:
                # same group, ignore
                continue
            if (
                keypath in keymap1 and
                keypath in keymap2 and
                chain1[index1] not in chain2[index2].subgroups and
                chain2[index2] not in chain1[index1].subgroups
            ):
                bad_keypath = keypath
                bad_group1 = chain1[index1]
                bad_group2 = chain2[index2]

    if bad_keypath is not None:
        raise RepositoryError(_(
            "Conflicting metadata keys between groups '{group1}' and '{group2}' on node '{node}':\n\n"
            "    metadata['{keypath}']\n\n"
            "You must either connect both groups through subgroups or have them not define "
            "conflicting metadata keys. Otherwise there is no way for BundleWrap to determine "
            "which group's metadata should win when they are merged."
        ).format(
            keypath="']['".join(bad_keypath),
            group1=bad_group1.name,
            group2=bad_group2.name,
            node=node_name,
        ))


class MetadataJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Fault):
            return obj.value
        if isinstance(obj, set):
            return sorted(obj)
        if isinstance(obj, bytes):
            return force_text(obj)
        else:
            raise ValueError(_("illegal metadata value type: {value} is {type}").format(
                type=type(obj),
                value=repr(obj),
            ))


def metadata_to_json(metadata, sort_keys=True):
    if not isinstance(metadata, dict):  # might be NodeMetadataProxy
        metadata = dict(metadata)
    return dumps(
        metadata,
        cls=MetadataJSONEncoder,
        indent=4,
        sort_keys=sort_keys,
    )


def hash_metadata(sdict):
    """
    Returns a canonical SHA1 hash to describe this dict.
    """
    return sha1(metadata_to_json(sdict).encode('utf-8')).hexdigest()
