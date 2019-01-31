# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from copy import copy
from hashlib import sha1
from json import dumps, JSONEncoder

from .exceptions import RepositoryError
from .utils import Fault
from .utils.dicts import ATOMIC_TYPES, map_dict_keys, merge_dict, value_at_key_path
from .utils.text import force_text, mark_for_translation as _


try:
    text_type = unicode
    byte_type = str
except NameError:
    text_type = str
    byte_type = bytes

METADATA_TYPES = (
    bool,
    byte_type,
    Fault,
    int,
    text_type,
    type(None),
)

# constants returned as options by metadata processors
DONE = 1
RUN_ME_AGAIN = 2
DEFAULTS = 3
OVERWRITE = 4


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


def blame_changed_paths(old_dict, new_dict, blame_dict, blame_name, defaults=False):
    def is_mergeable(value1, value2):
        if isinstance(value1, (list, set, tuple)) and isinstance(value2, (list, set, tuple)):
            return True
        elif isinstance(value1, dict) and isinstance(value2, dict):
            return True
        return False

    new_paths = map_dict_keys(new_dict)

    # clean up removed paths from blame_dict
    for path in list(blame_dict.keys()):
        if path not in new_paths:
            del blame_dict[path]

    for path in new_paths:
        new_value = value_at_key_path(new_dict, path)
        try:
            old_value = value_at_key_path(old_dict, path)
        except KeyError:
            blame_dict[path] = (blame_name,)
        else:
            if old_value != new_value:
                if defaults or is_mergeable(old_value, new_value):
                    blame_dict[path] += (blame_name,)
                else:
                    blame_dict[path] = (blame_name,)
    return blame_dict


def check_metadata_keys(node):
    try:
        basestring
    except NameError:  # Python 2
        basestring = str
    for path in map_dict_keys(node.metadata):
        value = path[-1]
        if not isinstance(value, basestring):
            raise TypeError(_("metadata key for {node} at path '{path}' is not a string").format(
                node=node.name,
                path="'->'".join(path[:-1]),
            ))


def check_metadata_processor_result(result, node_name, metadata_processor_name):
    """
    Validates the return value of a metadata processor and splits it
    into metadata and options.
    """
    if not isinstance(result, tuple) or not len(result) >= 2:
        raise ValueError(_(
            "metadata processor {metaproc} for node {node} did not return "
            "a tuple of length 2 or greater"
        ).format(
            metaproc=metadata_processor_name,
            node=node_name,
        ))
    result_dict, options = result[0], result[1:]
    if not isinstance(result_dict, dict):
        raise ValueError(_(
            "metadata processor {metaproc} for node {node} did not return "
            "a dict as the first element"
        ).format(
            metaproc=metadata_processor_name,
            node=node_name,
        ))
    for option in options:
        if option not in (DEFAULTS, DONE, RUN_ME_AGAIN, OVERWRITE):
            raise ValueError(_(
                "metadata processor {metaproc} for node {node} returned an "
                "invalid option: {opt}"
            ).format(
                metaproc=metadata_processor_name,
                node=node_name,
                opt=repr(option),
            ))
    if DONE in options and RUN_ME_AGAIN in options:
        raise ValueError(_(
            "metadata processor {metaproc} for node {node} cannot return both "
            "DONE and RUN_ME_AGAIN"
        ).format(
            metaproc=metadata_processor_name,
            node=node_name,
        ))
    if DONE not in options and RUN_ME_AGAIN not in options:
        raise ValueError(_(
            "metadata processor {metaproc} for node {node} must return either "
            "DONE or RUN_ME_AGAIN"
        ).format(
            metaproc=metadata_processor_name,
            node=node_name,
        ))
    if DEFAULTS in options and OVERWRITE in options:
        raise ValueError(_(
            "metadata processor {metaproc} for node {node} cannot return both "
            "DEFAULTS and OVERWRITE"
        ).format(
            metaproc=metadata_processor_name,
            node=node_name,
        ))
    return result_dict, options


def check_for_unsolvable_metadata_key_conflicts(node):
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
            metadata = merge_dict(metadata, group.metadata)
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


def deepcopy_metadata(obj):
    """
    Our own version of deepcopy.copy that doesn't pickle and ensures
    a limited range of types is used in metadata.
    """
    if isinstance(obj, METADATA_TYPES):
        return obj
    elif isinstance(obj, dict):
        if isinstance(obj, ATOMIC_TYPES[dict]):
            new_obj = atomic({})
        else:
            new_obj = {}
        for key, value in obj.items():
            if not isinstance(key, METADATA_TYPES):
                raise ValueError(_("illegal metadata key type: {}").format(repr(key)))
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
        raise ValueError(_("illegal metadata value type: {}").format(repr(obj)))
    return new_obj


def find_groups_causing_metadata_conflict(node_name, chain1, chain2, keypath):
    """
    Given two chains (lists of groups), find one group in each chain
    that has conflicting metadata with the other for the given key path.
    """
    chain1_metadata = [list(map_dict_keys(group.metadata)) for group in chain1]
    chain2_metadata = [list(map_dict_keys(group.metadata)) for group in chain2]

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
            raise ValueError(_("illegal metadata value type: {}").format(repr(obj)))


def hash_metadata(sdict):
    """
    Returns a canonical SHA1 hash to describe this dict.
    """
    return sha1(dumps(
        sdict,
        cls=MetadataJSONEncoder,
        indent=None,
        sort_keys=True,
    ).encode('utf-8')).hexdigest()
