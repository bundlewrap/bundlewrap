import readline
from code import interact
from os.path import isfile, join
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
        # read 'bw debug' history, if it exists
        history_filename = join(repo.path, '.bw_debug_history')
        if isfile(history_filename):
            readline.read_history_file(history_filename)

        # set up tab completion
        readline.set_completer(Completer(env).complete)
        readline.parse_and_bind("tab: complete")

        # launch interactive debug session
        interact(banner=banner, local=env)

        # save history
        readline.write_history_file(history_filename)
