# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from json import dumps

from ..exceptions import NoSuchGroup, NoSuchNode
from ..utils.text import red, mark_for_translation as _


def bw_metadata(repo, args):
    try:
        target = repo.get_node(args.target)
    except NoSuchNode:
        try:
            target = repo.get_group(args.target)
        except NoSuchGroup:
            yield _("{x} Node or group matching '{target}' not found").format(
                target=args.target,
                x=red("!!!"),
            )
            yield 1
            raise StopIteration()

    for line in dumps(target.metadata, indent=4).splitlines():
        yield line
