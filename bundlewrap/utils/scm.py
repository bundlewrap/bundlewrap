from shlex import quote
from subprocess import CalledProcessError, check_output, STDOUT

from .text import mark_for_translation as _


def get_git_branch():
    try:
        return check_output(
            "git rev-parse --abbrev-ref HEAD",
            shell=True,
            stderr=STDOUT,
        ).decode().strip()
    except CalledProcessError:
        return None


def get_git_clean():
    try:
        return not bool(check_output(
            "git status --porcelain",
            shell=True,
            stderr=STDOUT,
        ).decode().strip())
    except CalledProcessError:
        return None


def get_bzr_rev():
    try:
        return check_output(
            "bzr revno",
            shell=True,
            stderr=STDOUT,
        ).decode().strip()
    except CalledProcessError:
        return None


def get_git_rev():
    try:
        return check_output(
            "git rev-parse HEAD",
            shell=True,
            stderr=STDOUT,
        ).decode().strip()
    except CalledProcessError:
        return None


def get_hg_rev():
    try:
        return check_output(
            "hg --debug id -i",
            shell=True,
            stderr=STDOUT,
        ).decode().strip().rstrip("+")
    except CalledProcessError:
        return None


def get_rev():
    for scm_rev in (get_git_rev, get_hg_rev, get_bzr_rev):
        rev = scm_rev()
        if rev is not None:
            return rev
    return None


def set_git_rev(rev, detach=False):
    if not get_git_clean():
        raise RuntimeError(_("git working dir not clean, won't change rev"))
    if detach:
        command = "git checkout --detach {}".format(quote(rev))
    else:
        command = "git checkout {}".format(quote(rev))
    check_output(
        command,
        shell=True,
        stderr=STDOUT,
    )
