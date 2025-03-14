from os import mkdir
from os.path import exists, join
import re

from tomlkit import dumps as toml_dump, parse as toml_parse

from .exceptions import NoSuchGroup, NoSuchNode, RepositoryError
from .utils import (
    cached_property,
    cached_property_set,
    error_context,
    Fault,
    get_file_contents,
    names,
)
from .utils.dicts import (
    dict_to_toml,
    hash_statedict,
    set_key_at_path,
    normalize_dict,
    validate_dict,
    COLLECTION_OF_STRINGS,
    LIST_OR_TUPLE_OF_INTS,
)
from .utils.text import mark_for_translation as _, toml_clean, validate_name


GROUP_ATTR_DEFAULTS = {
    'cmd_wrapper_inner': "export LANG=C; {}",
    'cmd_wrapper_outer': "sudo -u {1} sh -c {0}",
    'lock_dir': "/var/lib/bundlewrap",
    'dummy': False,
    'ipmi_hostname': None,
    'ipmi_interface': None,
    'ipmi_username': None,
    'ipmi_password': None,
    'kubectl_context': None,
    'locking_node': None,
    'os': 'linux',
    # Setting os_version to 0 by default will probably yield less
    # surprises than setting it to max_int. Users will probably
    # start at a certain version and then gradually update their
    # systems, adding conditions like this:
    #
    #   if node.os_version >= (2,):
    #       new_behavior()
    #   else:
    #       old_behavior()
    #
    # If we set os_version to max_int, nodes without an explicit
    # os_version would automatically adopt the new_behavior() as
    # soon as it appears in the repo - which is probably not what
    # people want.
    'os_version': (0,),
    'password': None,
    # On some nodes, we maybe have pip2 and pip3 installed, but there's
    # no way of knowing which one the user wants. Or maybe there's only
    # one of them, but there's no symlink to pip, only pip3.
    'pip_command': 'pip',
    'use_shadow_passwords': True,
    'username': None,
}

GROUP_ATTR_TYPES = {
    'bundles': COLLECTION_OF_STRINGS,
    'cmd_wrapper_inner': str,
    'cmd_wrapper_outer': str,
    'dummy': bool,
    'file_path': str,
    'ipmi_hostname': (str, type(None)),
    'ipmi_interface': (str, type(None)),
    'ipmi_username': (str, Fault, type(None)),
    'ipmi_password': (str, Fault, type(None)),
    'kubectl_context': (str, type(None)),
    'lock_dir': str,
    'locking_node': (str, type(None)),
    'member_patterns': COLLECTION_OF_STRINGS,
    'members': COLLECTION_OF_STRINGS,
    'metadata': dict,
    'os': str,
    'os_version': LIST_OR_TUPLE_OF_INTS,
    'password': (Fault, str, type(None)),
    'pip_command': str,
    'subgroup_patterns': COLLECTION_OF_STRINGS,
    'subgroups': COLLECTION_OF_STRINGS,
    'supergroups': COLLECTION_OF_STRINGS,
    'use_shadow_passwords': bool,
    'username': (Fault, str, type(None)),
}

GROUP_ATTR_TYPES_ENFORCED = {
    'os_version': tuple,
}


def _build_error_chain(loop_node, last_node, nodes_in_between):
    """
    Used to illustrate subgroup loop paths in error messages.

    loop_node:          name of node that loops back to itself
    last_node:          name of last node pointing back to loop_node,
                        causing the loop
    nodes_in_between:   names of nodes traversed during loop detection,
                        does include loop_node if not a direct loop,
                        but not last_node
    """
    error_chain = []
    for visited in nodes_in_between:
        if (loop_node in error_chain) != (loop_node == visited):
            error_chain.append(visited)
    error_chain.append(last_node)
    error_chain.append(loop_node)
    return error_chain


class Group:
    """
    A group of nodes.
    """
    def __init__(self, group_name, attributes=None):
        if attributes is None:
            attributes = {}

        if not validate_name(group_name):
            raise RepositoryError(_("'{}' is not a valid group name.").format(group_name))

        with error_context(group_name=group_name):
            validate_dict(attributes, GROUP_ATTR_TYPES)

        attributes = normalize_dict(attributes, GROUP_ATTR_TYPES_ENFORCED)

        self._attributes = attributes
        self._immediate_subgroup_patterns = {
            re.compile(pattern) for pattern in
            set(attributes.get('subgroup_patterns', set()))
        }
        self._member_patterns = {
            re.compile(pattern) for pattern in
            set(attributes.get('member_patterns', set()))
        }
        self.name = group_name
        self.file_path = attributes.get('file_path')

        for attr in GROUP_ATTR_DEFAULTS:
            # defaults are applied in node.py
            setattr(self, attr, attributes.get(attr))

    def __lt__(self, other):
        return self.name < other.name

    def __repr__(self):
        return "<Group: {}>".format(self.name)

    def __str__(self):
        return self.name

    @cached_property
    def cdict(self):
        group_dict = {}
        for node in self.nodes:
            group_dict[node.name] = node.hash()
        return group_dict

    def group_membership_hash(self):
        return hash_statedict(sorted(names(self.nodes)))

    def hash(self):
        return hash_statedict(self.cdict)

    def metadata_hash(self):
        group_dict = {}
        for node in self.nodes:
            group_dict[node.name] = node.metadata_hash()
        return hash_statedict(group_dict)

    @property
    def node_count(self):
        return len(self.nodes)

    @cached_property_set
    def nodes(self):
        for node in self.repo.nodes:
            if node.in_group(self.name):
                yield node

    @cached_property_set
    def _nodes_from_members(self):
        for node_name in self._attributes.get('members', set()):
            try:
                yield self.repo.get_node(node_name)
            except NoSuchNode:
                raise RepositoryError(_(
                    "Group '{group}' has '{node}' listed as a member, "
                    "but no such node could be found."
                ).format(
                    group=self.name,
                    node=node_name,
                ))

    @property
    def _subgroup_names_from_patterns(self):
        for pattern in self._immediate_subgroup_patterns:
            for group in self.repo.groups:
                if pattern.search(group.name) is not None and group != self:
                    yield group.name

    @cached_property_set
    def _supergroups_from_attribute(self):
        for supergroup_name in self._attributes.get('supergroups', set()):
            try:
                supergroup = self.repo.get_group(supergroup_name)
            except NoSuchGroup:
                raise RepositoryError(_(
                    "Group '{group}' has '{supergroup}' listed as a supergroup in groups.py, "
                    "but no such group could be found."
                ).format(
                    group=self.name,
                    supergroup=supergroup_name,
                ))
            if self.name in (
                list(supergroup._attributes.get('subgroups', set())) +
                list(supergroup._subgroup_names_from_patterns)
            ):
                raise RepositoryError(_(
                    "Group '{group}' has '{supergroup}' listed as a supergroup in groups.py, "
                    "but it is already listed as a subgroup on that group (redundant)."
                ).format(
                    group=self.name,
                    supergroup=supergroup_name,
                ))
            yield supergroup

    def _check_subgroup_names(self, visited_names):
        """
        Recursively finds subgroups and checks for loops.
        """
        for name in self._immediate_subgroup_names:
            if name not in visited_names:
                try:
                    group = self.repo.get_group(name)
                except NoSuchGroup:
                    raise RepositoryError(_(
                        "Group '{group}' has '{subgroup}' listed as a subgroup in groups.py, "
                        "but no such group could be found."
                    ).format(
                        group=self.name,
                        subgroup=name,
                    ))
                for group_name in group._check_subgroup_names(
                    visited_names + [self.name],
                ):
                    yield group_name
            else:
                error_chain = _build_error_chain(
                    name,
                    self.name,
                    visited_names,
                )
                raise RepositoryError(_(
                    "Group '{group}' can't be a subgroup of itself. "
                    "({chain})"
                ).format(
                    group=name,
                    chain=" -> ".join(error_chain),
                ))
        if self.name not in visited_names:
            yield self.name

    @cached_property_set
    def parent_groups(self):
        for group in self.repo.groups:
            if self in group.subgroups:
                yield group

    @cached_property_set
    def immediate_parent_groups(self):
        for group in self.repo.groups:
            if self in group.immediate_subgroups:
                yield group

    @cached_property_set
    def subgroups(self):
        """
        Iterator over all subgroups as group objects.
        """
        for group_name in set(self._check_subgroup_names([self.name])):
            yield self.repo.get_group(group_name)

    @cached_property
    def toml(self):
        if not self.file_path or not self.file_path.endswith(".toml"):
            raise ValueError(_("group {} not in TOML format").format(self.name))
        return toml_parse(get_file_contents(self.file_path))

    def toml_save(self):
        try:
            toml_doc = self.toml
        except ValueError:
            attributes = self._attributes.copy()
            del attributes['file_path']
            toml_doc = dict_to_toml(attributes)
            self.file_path = join(self.repo.path, "groups", self.name + ".toml")
        if not exists(join(self.repo.path, "groups")):
            mkdir(join(self.repo.path, "groups"))
        with open(self.file_path, 'w') as f:
            f.write(toml_clean(toml_dump(toml_doc)))

    def toml_set(self, path, value):
        if not isinstance(path, tuple):
            path = path.split("/")
        set_key_at_path(self.toml, path, value)

    @cached_property_set
    def immediate_subgroups(self):
        """
        Iterator over all immediate subgroups as group objects.
        """
        for group_name in self._immediate_subgroup_names:
            try:
                yield self.repo.get_group(group_name)
            except NoSuchGroup:
                raise RepositoryError(_(
                    "Group '{group}' has '{subgroup}' listed as a subgroup in groups.py, "
                    "but no such group could be found."
                ).format(
                    group=self.name,
                    subgroup=group_name,
                ))

    @cached_property_set
    def _immediate_subgroup_names(self):
        return (
            list(self._attributes.get('subgroups', set())) +
            list(self._subgroup_names_from_patterns) +
            [group.name for group in self.repo.groups if self in group._supergroups_from_attribute]
        )
