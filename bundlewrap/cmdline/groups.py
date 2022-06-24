from ..group import GROUP_ATTR_DEFAULTS
from ..utils.text import bold, mark_for_translation as _
from ..utils.ui import io
from .nodes import attribute_table, attrs_for_entities, select_attrs


GROUP_ATTRS = sorted(list(GROUP_ATTR_DEFAULTS) + ['nodes', 'node_count'])


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
            selected_attrs, available_attrs = select_attrs(
                args['attrs'],
                GROUP_ATTRS,
            )
            results = attrs_for_entities(
                groups,
                selected_attrs,
                1,  # groups don't have dynamic attrs like nodes
            )
            attribute_table(
                results,
                bold(_("group")),
                selected_attrs,
                available_attrs,
                args['inline'],
            )
