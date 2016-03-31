# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from code import interact

from .. import VERSION_STRING
from ..utils.text import mark_for_translation as _
from ..utils.ui import io


DEBUG_BANNER = _("BundleWrap {version} interactive repository inspector\n"
                 "> You can access the current repository as 'repo'."
                 "").format(version=VERSION_STRING)

DEBUG_BANNER_NODE = DEBUG_BANNER + "\n" + \
    _("> You can access the selected node as 'node'.")


def bw_debug(repo, args):
    io.deactivate()
    if args['node'] is None:
        env = {'repo': repo}
        banner = DEBUG_BANNER
    else:
        env = {'node': repo.get_node(args['node']), 'repo': repo}
        banner = DEBUG_BANNER_NODE

    if args['command']:
        exec(args['command'], env)
    else:
        interact(banner, local=env)
