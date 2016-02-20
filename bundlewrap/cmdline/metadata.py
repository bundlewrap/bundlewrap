# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from json import dumps, JSONEncoder

from ..exceptions import NoSuchNode
from ..utils.text import force_text, mark_for_translation as _, red


class ReprJSONEncoder(JSONEncoder):
    def default(self, obj):
        return repr(obj)


def bw_metadata(repo, args):
    try:
        node = repo.get_node(args['node'])
    except NoSuchNode:
        yield _("{x} No such node: {node}").format(
            node=args['node'],
            x=red("!!!"),
        )
        yield 1
        raise StopIteration()

    for line in dumps(node.metadata, cls=ReprJSONEncoder, indent=4).splitlines():
        yield force_text(line)
