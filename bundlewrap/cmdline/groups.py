from ..group import GROUP_ATTR_DEFAULTS
from ..utils.text import bold, mark_for_translation as _
from ..utils.ui import io
from .nodes import _attribute_table


GROUP_ATTRS = sorted(list(GROUP_ATTR_DEFAULTS) + ['nodes'])
GROUP_ATTRS_LISTS = ('nodes',)


def bw_groups(repo, args):
    if not args['groups']:
        for group in sorted(repo.groups):
            io.stdout(group.name)
    else:
        groups = {repo.get_group(group.strip()) for group in args['groups']}
        if not args['attrs']:
            subgroups = groups.copy()
            for group in groups:
                subgroups.update(group.subgroups)
            for subgroup in sorted(subgroups):
                io.stdout(subgroup.name)
        else:
            _attribute_table(
                groups,
                bold(_("group")),
                args['attrs'],
                GROUP_ATTRS,
                GROUP_ATTRS_LISTS,
                args['inline'],
            )
