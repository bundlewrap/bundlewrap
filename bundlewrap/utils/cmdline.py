from functools import wraps
from os import environ
from sys import exit, stderr, stdout
from traceback import print_exc

from ..exceptions import NoSuchGroup, NoSuchItem, NoSuchNode
from .text import mark_for_translation as _, red
from .ui import io, QUIT_EVENT


def exit_on_keyboardinterrupt(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except KeyboardInterrupt:
            exit(130)  # https://tldp.org/LDP/abs/html/exitcodes.html
    return wrapper


def suppress_broken_pipe_msg(f):
    """
    Oh boy.

    CPython does funny things with SIGPIPE. By default, it is caught and
    raised as a BrokenPipeError. When do we get a SIGPIPE? Most commonly
    when piping into head:

        bw nodes | head -n 1

    head will exit after receiving the first line, causing the kernel to
    send SIGPIPE to our process. Since in most cases, we can't just quit
    early, we simply ignore BrokenPipeError in utils.ui.write_to_stream.

    Unfortunately, Python will still print a message:

        Exception ignored in: <_io.TextIOWrapper name='<stdout>'
                               mode='w' encoding='UTF-8'>
        BrokenPipeError: [Errno 32] Broken pipe

    See also http://bugs.python.org/issue11380. The crazy try/finally
    construct below is taken from there and I quote:

        This will:
         - capture any exceptions *you've* raised as the context for the
           errors raised in this handler
         - expose any exceptions generated during this thing itself
         - prevent the interpreter dying during shutdown in
           flush_std_files by closing the files (you can't easily wipe
           out the pending writes that have failed)

    CAVEAT: There is a seamingly easier method floating around on the
    net (http://stackoverflow.com/a/16865106) that restores the default
    behavior for SIGPIPE (i.e. not turning it into a BrokenPipeError):

        from signal import signal, SIGPIPE, SIG_DFL
        signal(SIGPIPE,SIG_DFL)

    This worked fine for a while but broke when using
    multiprocessing.Manager() to share the list of jobs in utils.ui
    between processes. When the main process terminated, it quit with
    return code 141 (indicating a broken pipe), and the background
    process used for the manager continued to hang around indefinitely.
    Bonus fun: This was observed only on Ubuntu Trusty (14.04).
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception:
            print_exc()
            exit(1)
        finally:
            try:
                stdout.flush()
            finally:
                try:
                    stdout.close()
                finally:
                    try:
                        stderr.flush()
                    finally:
                        stderr.close()
    return wrapper


def count_items(nodes):
    count = 0
    for node in nodes:
        if QUIT_EVENT.is_set():
            return 0
        count += len(node.items)
    return count


def get_group(repo, group_name):
    try:
        return repo.get_group(group_name)
    except NoSuchGroup:
        io.stderr(_("{x} No such group: {group}").format(
            group=group_name,
            x=red("!!!"),
        ))
        exit(1)


def get_item(node, item_id):
    try:
        return node.get_item(item_id)
    except NoSuchItem:
        io.stderr(_("{x} No such item on node '{node}': {item}").format(
            item=item_id,
            node=node.name,
            x=red("!!!"),
        ))
        exit(1)


def get_node(repo, node_name):
    try:
        return repo.get_node(node_name)
    except NoSuchNode:
        io.stderr(_("{x} No such node: {node}").format(
            node=node_name,
            x=red("!!!"),
        ))
        exit(1)



DEFAULT_item_workers = int(environ.get("BW_ITEM_WORKERS", "4"))
DEFAULT_node_workers = int(environ.get("BW_NODE_WORKERS", "4"))
DEFAULT_softlock_expiry = environ.get("BW_SOFTLOCK_EXPIRY", "8h")

HELP_get_target_nodes = _("""expression to select target nodes:

my_node            # to select a single node
my_group           # all nodes in this group
bundle:my_bundle   # all nodes with this bundle
!bundle:my_bundle  # all nodes without this bundle
!group:my_group    # all nodes not in this group
"lambda:node.metadata_get('foo/magic', 47) < 3"
                   # all nodes whose metadata["foo"]["magic"] is less than three
""")
HELP_item_workers = _("number of items to apply simultaneously on each node (defaults to {})").format(DEFAULT_item_workers)
HELP_node_workers = _("number of nodes to apply to simultaneously (defaults to {})").format(DEFAULT_node_workers)
HELP_softlock_expiry = _("how long before the lock is ignored and removed automatically (defaults to \"{}\")").format(DEFAULT_softlock_expiry)


def get_target_nodes(repo, target_strings, node_workers=None):
    if not node_workers:
        node_workers = DEFAULT_node_workers

    nodes_matching = repo.nodes_matching(target_strings, node_workers)
    if not nodes_matching:
        io.stderr(_("{x} Input did not match any nodes").format(
            x=red("!!!"),
        ))
        exit(1)

    return nodes_matching
