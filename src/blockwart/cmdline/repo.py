from code import interact

from .. import VERSION_STRING
from ..repo import Repository
from ..utils.text import mark_for_translation as _


DEBUG_BANNER = _("blockwart {} interactive repository inspector\n"
                 "> You can access the current repository as 'repo'."
                 "").format(VERSION_STRING)

DEBUG_BANNER_NODE = DEBUG_BANNER + "\n" + \
    _("> You can access the selected node as 'node'.")


def bw_repo_create(repo, args):
    repo.create()


def bw_repo_debug(repo, args):
    repo = Repository(repo.path, skip_validation=False)
    if args.node is None:
        interact(DEBUG_BANNER, local={'repo': repo})
    else:
        node = repo.get_node(args.node)
        interact(DEBUG_BANNER_NODE, local={'node': node, 'repo': repo})
