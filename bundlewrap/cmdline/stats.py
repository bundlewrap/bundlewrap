from operator import itemgetter

from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import bold, mark_for_translation as _
from ..utils.ui import page_lines


def bw_stats(repo, args):
    items = {}
    metadata_defaults = set()
    metadata_reactors = set()
    for node in repo.nodes:
        for metadata_default_name, metadata_default in node.metadata_defaults:
            metadata_defaults.add(metadata_default_name)
        for metadata_reactor_name, metadata_reactor in node.metadata_reactors:
            metadata_reactors.add(metadata_reactor_name)
        for item in node.items:
            items.setdefault(item.ITEM_TYPE_NAME, 0)
            items[item.ITEM_TYPE_NAME] += 1

    rows = [
        [
            bold(_("count")),
            bold(_("type")),
        ],
        ROW_SEPARATOR,
        [str(len(repo.nodes)), _("nodes")],
        [str(len(repo.groups)), _("groups")],
        [str(len(repo.bundle_names)), _("bundles")],
        [str(len(metadata_defaults)), _("metadata defaults")],
        [str(len(metadata_reactors)), _("metadata reactors")],
        [str(sum([len(list(node.items)) for node in repo.nodes])), _("items")],
        ROW_SEPARATOR,
    ]

    for item_type, count in sorted(items.items(), key=itemgetter(1), reverse=True):
        rows.append([str(count), item_type])

    page_lines(render_table(rows, alignments={0: 'right'}))
