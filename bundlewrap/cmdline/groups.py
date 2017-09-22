# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..group import GROUP_ATTR_DEFAULTS
from ..utils.text import bold, mark_for_translation as _
from ..utils.ui import io
from .nodes import _attribute_table


GROUP_ATTRS = sorted(list(GROUP_ATTR_DEFAULTS) + ['nodes'])
GROUP_ATTRS_LISTS = ('nodes',)


def bw_groups(repo, args):
    if not args['groups']:
        for group in repo.groups:
            io.stdout(group.name)
    else:
        groups = [repo.get_group(group.strip()) for group in args['groups'].split(",")]
        if not args['attrs']:
            nodes = set()
            for group in groups:
                nodes = nodes.union(group.nodes)
            for node in sorted(nodes):
                io.stdout(node.name)
        else:
            _attribute_table(
                groups,
                bold(_("group")),
                args['attrs'],
                GROUP_ATTRS,
                GROUP_ATTRS_LISTS,
                args['inline'],
            )
