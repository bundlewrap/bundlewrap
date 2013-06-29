from code import interact

from .. import VERSION_STRING
from ..repo import Repository
from ..utils import mark_for_translation as _


DEBUG_BANNER = _("blockwart {} interactive repository inspector\n"
                 "> You can access the current repository as 'repo'."
                 "").format(VERSION_STRING)


def bw_repo_create(repo, args):
    repo.create()
    return ()


def bw_repo_debug(repo, args):
    repo = Repository(repo.path, skip_validation=False)
    interact(DEBUG_BANNER, local={'repo': repo})
    return ()
