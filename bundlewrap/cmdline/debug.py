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
            previous_history_length = readline.get_current_history_length()
        else:
            # touch empty history file so we can append to it (maybe, see
            # comment below)
            open(history_filename, 'wb').close()
            previous_history_length = 0

        # set up tab completion
        readline.set_completer(Completer(env).complete)
        readline.parse_and_bind("tab: complete")

        # launch interactive debug session
        interact(banner=banner, local=env)

        # So, the thing is, MacOS does not use GNU readline, but instead
        # provides you with `editline` as a wrapper. This usually works fine,
        # except it doesn't implement `append_history_file()` at all.
        # So we have to find out if append_history_file is supported, and if
        # not we just overwrite the history file with whatever history the last
        # closed `bw debug` shell had. This sucks, but that's what we have to
        # work with.
        if hasattr(readline, 'append_history_file'):
            new_history_length = readline.get_current_history_length()
            readline.set_history_length(10000)
            readline.append_history_file(
                new_history_length - previous_history_length,
                history_filename,
            )
        else:
            readline.set_history_length(10000)
            readline.write_history_file(history_filename)
