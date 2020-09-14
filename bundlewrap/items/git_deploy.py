from atexit import register as at_exit
from hashlib import md5
from os import getenv, getpid, makedirs, mkdir, remove, rmdir, setpgrp
from os.path import isfile, join
from shlex import quote
from shutil import rmtree
from subprocess import PIPE, Popen
from tempfile import gettempdir, NamedTemporaryFile
from time import sleep

from bundlewrap.exceptions import BundleError, RepositoryError
from bundlewrap.items import Item
from bundlewrap.utils import cached_property
from bundlewrap.utils.text import is_subdirectory, mark_for_translation as _, randstr
from bundlewrap.utils.ui import io


REPO_MAP_FILENAME = "git_deploy_repos"
REMOTE_STATE_FILENAME = ".bundlewrap_git_deploy"


def is_ref(rev):
    """
    Braindead check to see if our rev is a branch or tag name. False
    negatives are OK since this is only used for optimization.
    """
    for char in rev:
        if char not in "0123456789abcdef":
            return True
    return False


def clone_to_dir(remote_url, rev):
    """
    Clones the given URL to a temporary directory, using a shallow clone
    if the given revision is definitely not a commit hash. Clones to
    the base directory $BW_GIT_DEPLOY_CACHE if set.

    Returns the path to the repo directory and to another directory to
    be deleted when the process exits (may be None).
    """
    repo_dir_hashed = md5(remote_url.encode('UTF-8')).hexdigest()

    cache_dir_env = getenv("BW_GIT_DEPLOY_CACHE")
    if cache_dir_env:
        # Do not remove this, because it was not created by us.
        remove_dir = None
        repo_dir = join(cache_dir_env, repo_dir_hashed)
        lock_dir = join(cache_dir_env, repo_dir_hashed + ".bw_lock")
    else:
        remove_dir = join(gettempdir(), "bw-git-cache-{}".format(getpid()))
        repo_dir = join(remove_dir, repo_dir_hashed)
        lock_dir = join(remove_dir, repo_dir_hashed + ".bw_lock")

    makedirs(repo_dir, exist_ok=True)

    io.debug(_("{pid}: lock_dir {lock_dir}").format(lock_dir=lock_dir, pid=getpid()))
    io.debug(_("{pid}: remove_dir {remove_dir}").format(remove_dir=remove_dir, pid=getpid()))
    io.debug(_("{pid}: repo_dir {repo_dir}").format(repo_dir=repo_dir, pid=getpid()))

    if is_ref(rev) and not remote_url.startswith('http'):
        git_cmdline = ["clone", "--bare", "--depth", "1", "--no-single-branch", remote_url, "."]
    else:
        git_cmdline = ["clone", "--bare", remote_url, "."]

    # Use a lock directory to cooperate with other running instances
    # of bw (in cases where $BW_GIT_DEPLOY_CACHE is used).
    while True:
        try:
            mkdir(lock_dir)
            io.debug(_("{pid}: Have lock on {lock_dir}").format(
                lock_dir=lock_dir,
                pid=getpid(),
            ))
            break
        except FileExistsError:
            io.debug(_("{pid}: Waiting for lock on {lock_dir} ...").format(
                lock_dir=lock_dir,
                pid=getpid(),
            ))
            sleep(1)

    try:
        # We now have a lock, but another process may have cloned
        # the repo in the meantime. (It is vital to use a git command
        # here, which does not traverse to parent directories.)
        try:
            git_command(
                ["rev-parse", "--resolve-git-dir", "."],
                repo_dir,
                error_messages=False,
            )
            io.debug(_("{pid}: Repo already existed in {repo_dir}").format(
                repo_dir=repo_dir,
                pid=getpid(),
            ))
        except RuntimeError:
            git_command(git_cmdline, repo_dir)
            io.debug(_("{pid}: Cloned repo to {repo_dir}").format(
                repo_dir=repo_dir,
                pid=getpid(),
            ))
    finally:
        rmdir(lock_dir)
        io.debug(_("{pid}: Released lock on {lock_dir}").format(
            lock_dir=lock_dir,
            pid=getpid(),
        ))

    return repo_dir, remove_dir


def get_local_repo_path(bw_repo_path, repo_name):
    """
    From the given BundleWrap repo, get the filesystem path to the git
    repo associated with the given internal repo name.
    """
    repo_map_path = join(bw_repo_path, REPO_MAP_FILENAME)
    if not isfile(repo_map_path):
        io.stderr(_("missing repo map for git_deploy at {}").format(repo_map_path))
        io.stderr(_("you must create this file with the following format:"))
        io.stderr(_("  <value of repo attribute on git_deploy item>: "
                    "<absolute path to local git repo>"))
        io.stderr(_("since the path is local, you should also add the "
                    "{} file to your gitignore").format(REPO_MAP_FILENAME))
        raise RepositoryError(_("missing repo map for git_deploy"))

    with open(join(bw_repo_path, REPO_MAP_FILENAME)) as f:
        repo_map = f.readlines()

    for line in repo_map:
        if not line.strip() or line.startswith("#"):
            continue
        try:
            repo, path = line.split(":", 1)
        except:
            raise RepositoryError(_("unable to parse line from {path}: '{line}'").format(
                line=line,
                path=repo_map_path,
            ))
        if repo_name == repo:
            return path.strip()

    raise RepositoryError(_("no path found for repo '{repo}' in {path}").format(
        path=repo_map_path,
        repo=repo_name,
    ))


def git_command(cmdline, repo_dir, error_messages=True):
    """
    Runs the given git command line in the given directory.

    Returns stdout of the command.
    """
    cmdline = ["git"] + cmdline
    io.debug(_("running '{}' in {}").format(
        " ".join(cmdline),
        repo_dir,
    ))
    git_process = Popen(
        cmdline,
        cwd=repo_dir,
        preexec_fn=setpgrp,
        stderr=PIPE,
        stdout=PIPE,
    )
    stdout, stderr = git_process.communicate()
    # FIXME integrate this into Item._command_results
    if git_process.returncode != 0:
        if error_messages:
            io.stderr(_("{} failed command: {}").format(getpid(), " ".join(cmdline)))
            io.stderr(_("{} failed in dir: {}").format(getpid(), repo_dir))
            io.stderr(_("{} stdout:\n{}").format(getpid(), stdout))
            io.stderr(_("{} stderr:\n{}").format(getpid(), stderr))
        raise RuntimeError(_("`git {command}` failed in {dir}").format(
            command=cmdline[1],
            dir=repo_dir,
        ))
    return stdout.decode('utf-8').strip()


class GitDeploy(Item):
    """
    Facilitates deployment of a given rev from a local git repo to a
    node.
    """
    BUNDLE_ATTRIBUTE_NAME = "git_deploy"
    ITEM_ATTRIBUTES = {
        'repo': None,
        'rev': None,
        'use_xattrs': False,
    }
    ITEM_TYPE_NAME = "git_deploy"
    REQUIRED_ATTRIBUTES = ['repo', 'rev']

    def __repr__(self):
        return "<GitDeploy path:{} repo:{} rev:{}>".format(
            self.name,
            self.attributes['repo'],
            self.attributes['rev'],
        )

    @cached_property
    def _expanded_rev(self):
        git_cmdline = ["rev-parse", self.attributes['rev']]
        return git_command(
            git_cmdline,
            self._repo_dir,
        )

    @cached_property
    def _repo_dir(self):
        if "://" in self.attributes['repo']:
            repo_dir, remove_dir = clone_to_dir(self.attributes['repo'], self.attributes['rev'])
            if remove_dir is not None:
                io.debug(_("registering {} for deletion on exit").format(remove_dir))
                at_exit(rmtree, remove_dir, ignore_errors=True)
        else:
            repo_dir = get_local_repo_path(self.node.repo.path, self.attributes['repo'])
        return repo_dir

    def cdict(self):
        return {'rev': self._expanded_rev}

    def get_auto_deps(self, items):
        deps = set()
        for item in items:
            if item == self:
                continue
            if ((
                item.ITEM_TYPE_NAME == "file" and
                is_subdirectory(item.name, self.name)
            ) or (
                item.ITEM_TYPE_NAME in ("file", "symlink") and
                item.name == self.name
            )):
                raise BundleError(_(
                    "{item1} (from bundle '{bundle1}') blocking path to "
                    "{item2} (from bundle '{bundle2}')"
                ).format(
                    item1=item.id,
                    bundle1=item.bundle.name,
                    item2=self.id,
                    bundle2=self.bundle.name,
                ))
            if (
                item.ITEM_TYPE_NAME == "directory" and
                item.name == self.name
            ):
                if item.attributes['purge']:
                    raise BundleError(_(
                        "cannot git_deploy into purged directory {}"
                    ).format(item.name))
                else:
                    deps.add(item.id)
        return deps

    def fix(self, status):
        archive_local = NamedTemporaryFile(delete=False)
        try:
            archive_local.close()
            git_command(
                ["archive", "-o", archive_local.name, self._expanded_rev],
                self._repo_dir,
            )
            temp_filename = ".bundlewrap_tmp_git_deploy_" + randstr()

            try:
                self.node.upload(
                    archive_local.name,
                    temp_filename,
                )
                self.run("find {} -mindepth 1 -delete".format(quote(self.name)))
                self.run("tar -xf {} -C {}".format(temp_filename, quote(self.name)))
                if self.attributes['use_xattrs']:
                    self.run("attr -q -s bw_git_deploy_rev -V {} {}".format(
                        self._expanded_rev,
                        quote(self.name),
                    ))
                else:
                    self.run("echo {} > {}".format(
                        self._expanded_rev,
                        quote(join(self.name, REMOTE_STATE_FILENAME)),
                    ))
                    self.run("chmod 400 {}".format(
                        quote(join(self.name, REMOTE_STATE_FILENAME)),
                    ))
            finally:
                self.run("rm -f {}".format(temp_filename))
        finally:
            remove(archive_local.name)

    def sdict(self):
        if self.attributes['use_xattrs']:
            status_result = self.run(
                "attr -q -g bw_git_deploy_rev {}".format(quote(self.name)),
                may_fail=True,
            )
        else:
            status_result = self.run(
                "cat {}".format(quote(join(self.name, REMOTE_STATE_FILENAME))),
                may_fail=True,
            )
        if status_result.return_code != 0:
            return None
        else:
            return {'rev': status_result.stdout.decode('utf-8').strip()}

# FIXME get_auto_deps for dir and ensure dir does not use purge
