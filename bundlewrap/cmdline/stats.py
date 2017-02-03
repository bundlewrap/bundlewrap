# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from operator import itemgetter

from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import bold, mark_for_translation as _
from ..utils.ui import page_lines


def bw_stats(repo, args):
    items = {}
    metaprocs = set()
    for node in repo.nodes:
        for metadata_processor_name, metadata_processor in node.metadata_processors:
            metaprocs.add(metadata_processor_name)
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
        [str(len(metaprocs)), _("metadata processors")],
        [str(sum([len(list(node.items)) for node in repo.nodes])), _("items")],
        ROW_SEPARATOR,
    ]

    for item_type, count in sorted(items.items(), key=itemgetter(1), reverse=True):
        rows.append([str(count), item_type])

    page_lines(render_table(rows, alignments={0: 'right'}))
