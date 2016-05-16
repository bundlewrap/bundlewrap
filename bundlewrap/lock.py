from datetime import datetime
from getpass import getuser
import json
from os import environ
from pipes import quote
from socket import gethostname
from time import time

from .exceptions import NodeHardLockedException
from .utils import tempfile
from .utils.text import blue, bold, mark_for_translation as _, randstr, red, wrap_question
from .utils.ui import io


HARD_LOCK_PATH = "/tmp/bundlewrap.lock"
HARD_LOCK_FILE = HARD_LOCK_PATH + "/info"
SOFT_LOCK_PATH = "/tmp/bundlewrap.softlock.d"
SOFT_LOCK_FILE = "/tmp/bundlewrap.softlock.d/{id}"


def identity():
    return environ.get('BW_IDENTITY', "{}@{}".format(
        getuser(),
        gethostname(),
    ))


class HardNodeLock(object):
    def __init__(self, node, interactive, ignore=False):
        self.node = node
        self.ignore = ignore
        self.interactive = interactive

    def __enter__(self):
        with tempfile() as local_path:
            with io.job(_("  {node}  checking hard lock status...").format(node=self.node.name)):
                result = self.node.run("mkdir " + quote(HARD_LOCK_PATH), may_fail=True)
                if result.return_code != 0:
                    self.node.download(HARD_LOCK_FILE, local_path, ignore_failure=True)
                    with open(local_path, 'r') as f:
                        try:
                            info = json.loads(f.read())
                        except:
                            io.stderr(_(
                                "{warning}  corrupted lock on {node}: "
                                "unable to read or parse lock file contents "
                                "(clear it with `bw run {node} 'rm -R {path}'`)"
                            ).format(
                                node=self.node.name,
                                path=HARD_LOCK_FILE,
                                warning=red(_("WARNING")),
                            ))
                            info = {}
                    try:
                        d = info['date']
                    except KeyError:
                        info['date'] = _("<unknown>")
                        info['duration'] = _("<unknown>")
                    else:
                        info['date'] = datetime.fromtimestamp(d).strftime("%c")
                        info['duration'] = str(
                            datetime.now() - datetime.fromtimestamp(d)
                        ).split(".")[0]
                    if 'user' not in info:
                        info['user'] = _("<unknown>")
                    if self.ignore or (self.interactive and io.ask(
                        self._warning_message(info),
                        False,
                        epilogue=blue("?") + " " + bold(self.node.name),
                    )):
                        pass
                    else:
                        raise NodeHardLockedException(info)

            with io.job(_("  {node}  uploading lock file...").format(node=self.node.name)):
                with open(local_path, 'w') as f:
                    f.write(json.dumps({
                        'date': time(),
                        'user': identity(),
                    }))
                self.node.upload(local_path, HARD_LOCK_FILE)

    def __exit__(self, type, value, traceback):
        with io.job(_("  {node}  removing hard lock...").format(node=self.node.name)):
            result = self.node.run("rm -R {}".format(quote(HARD_LOCK_PATH)), may_fail=True)

        if result.return_code != 0:
            io.stderr(_("Could not release hard lock for node '{node}'").format(
                node=self.node.name,
            ))

    def _warning_message(self, info):
        return wrap_question(
            red(_("NODE LOCKED")),
            _(
                "Looks like somebody is currently using BundleWrap on this node.\n"
                "You should let them finish or override the lock if it has gone stale.\n"
                "\n"
                "locked by: {user}\n"
                "lock acquired: {duration} ago ({date})"
            ).format(
                user=bold(info['user']),
                date=info['date'],
                duration=bold(info['duration']),
            ),
            bold(_("Override lock?")),
            prefix="{x} {node} ".format(node=bold(self.node.name), x=blue("?")),
        )


def softlock_add(node, operations=None):
    if operations is None:
        operations = ["apply", "run"]
    lock_id = randstr(length=8).upper()

    content = json.dumps({
        'date': time(),
        'id': lock_id,
        'ops': operations,
        'user': identity(),
    }, indent=None, sort_keys=True)

    with tempfile() as local_path:
        with open(local_path, 'w') as f:
            f.write(content + "\n")
        node.run("mkdir -p " + quote(SOFT_LOCK_PATH))
        node.upload(local_path, SOFT_LOCK_FILE.format(id=lock_id))
