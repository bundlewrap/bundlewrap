# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from .exceptions import NoSuchGroup, NoSuchNode, RepositoryError
from .utils import cached_property
from .utils.statedict import hash_statedict
from .utils.text import mark_for_translation as _, validate_name


GROUP_ATTR_DEFAULTS = {
    'dummy': False,
    'os': 'linux',
    'use_shadow_passwords': True,
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


class Group(object):
    """
    A group of nodes.
    """
    def __init__(self, group_name, infodict=None):
        if infodict is None:
            infodict = {}

        if not validate_name(group_name):
            raise RepositoryError(_("'{}' is not a valid group name.").format(group_name))

        self.name = group_name
        self.bundle_names = infodict.get('bundles', [])
        self.immediate_subgroup_names = infodict.get('subgroups', [])
        self.metadata = infodict.get('metadata', {})
        self.patterns = infodict.get('member_patterns', [])
        self.static_member_names = infodict.get('members', [])

        for attr in GROUP_ATTR_DEFAULTS:
            # defaults are applied in node.py
            setattr(self, attr, infodict.get(attr))

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

    def hash(self):
        return hash_statedict(self.cdict)

    def metadata_hash(self):
        group_dict = {}
        for node in self.nodes:
            group_dict[node.name] = node.metadata_hash()
        return hash_statedict(group_dict)

    @cached_property
    def nodes(self):
        """
        List of all nodes in this group.
        """
        result = []
        result += list(self._nodes_from_static_members)
        result += list(self._nodes_from_subgroups)
        result += list(self._nodes_from_patterns)
        return sorted(set(result))

    @property
    def _nodes_from_static_members(self):
        for node_name in self.static_member_names:
            try:
                yield self.repo.get_node(node_name)
            except NoSuchNode:
                raise NoSuchNode(_(
                    "Group '{group}' has '{node}' listed as a member in groups.py, "
                    "but no such node could be found."
                ).format(
                    group=self.name,
                    node=node_name,
                ))

    @property
    def _nodes_from_subgroups(self):
        for subgroup in self.subgroups:
            for node in subgroup.nodes:
                yield node

    @property
    def _nodes_from_patterns(self):
        for pattern in self.patterns:
            compiled_pattern = re.compile(pattern)
            for node in self.repo.nodes:
                if not compiled_pattern.search(node.name) is None:
                    yield node

    def _check_subgroup_names(self, visited_names):
        """
        Recursively finds subgroups and checks for loops.
        """
        for name in self.immediate_subgroup_names:
            if name not in visited_names:
                try:
                    group = self.repo.get_group(name)
                except NoSuchGroup:
                    raise NoSuchGroup(_(
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
                    "({chain})").format(
                        group=name,
                        chain=" -> ".join(error_chain),
                    )
                )
        if self.name not in visited_names:
            yield self.name

    @cached_property
    def parent_groups(self):
        for group in self.repo.groups:
            if self in group.subgroups:
                yield group

    @cached_property
    def subgroups(self):
        """
        Iterator over all subgroups as group objects.
        """
        for group_name in self._check_subgroup_names([self.name]):
            yield self.repo.get_group(group_name)
