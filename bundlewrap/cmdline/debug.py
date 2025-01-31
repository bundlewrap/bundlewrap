from code import interact
from readline import set_completer, parse_and_bind
from rlcompleter import Completer

from .. import VERSION_STRING
from ..utils.cmdline import get_node
from ..utils.text import mark_for_translation as _
from ..utils.ui import io


DEBUG_BANNER = _("BundleWrap {version} interactive repository inspector\n"
                 "> You can access the current repository as 'repo'."
                 "").format(version=VERSION_STRING)

DEBUG_BANNER_NODE = DEBUG_BANNER + "\n" + \
    _("> You can access the selected node as 'node'.")


def bw_debug(repo, args):
    if args['node'] is None:
        env = {'repo': repo}
        banner = DEBUG_BANNER
    else:
        env = {'node': get_node(repo, args['node']), 'repo': repo}
        banner = DEBUG_BANNER_NODE

    io.deactivate()
    if args['command']:
        exec(args['command'], env)
    else:
        set_completer(Completer(env).complete)
        parse_and_bind("tab: complete")
        interact(banner=banner, local=env)
