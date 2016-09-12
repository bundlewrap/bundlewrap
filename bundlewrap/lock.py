from datetime import datetime
from getpass import getuser
import json
from os import environ
from pipes import quote
from socket import gethostname
from time import time

from .exceptions import NodeLockedException
from .utils import cached_property, tempfile
from .utils.text import blue, bold, mark_for_translation as _, red, wrap_question
from .utils.time import format_duration, format_timestamp, parse_duration
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


class NodeLock(object):
    def __init__(self, node, interactive=False, ignore=False):
        self.node = node
        self.ignore = ignore
        self.interactive = interactive

    def __enter__(self):
        with tempfile() as local_path:
            if not self.ignore:
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
                        expired = False
                        try:
                            d = info['date']
                        except KeyError:
                            info['date'] = _("<unknown>")
                            info['duration'] = _("<unknown>")
                        else:
                            duration = datetime.now() - datetime.fromtimestamp(d)
                            info['date'] = format_timestamp(d)
                            info['duration'] = format_duration(duration)
                            if duration > parse_duration(environ.get('BW_HARDLOCK_EXPIRY', "8h")):
                                expired = True
                                io.debug("ignoring expired hard lock on {}".format(self.node.name))
                        if 'user' not in info:
                            info['user'] = _("<unknown>")
                        if expired or self.ignore or (self.interactive and io.ask(
                            self._warning_message_hard(info),
                            False,
                            epilogue=blue("?") + " " + bold(self.node.name),
                        )):
                            pass
                        else:
                            raise NodeLockedException(info)

            with io.job(_("  {node}  uploading lock file...").format(node=self.node.name)):
                if self.ignore:
                    self.node.run("mkdir -p " + quote(HARD_LOCK_PATH))
                with open(local_path, 'w') as f:
                    f.write(json.dumps({
                        'date': time(),
                        'user': identity(),
                    }))
                self.node.upload(local_path, HARD_LOCK_FILE)

        return self

    def __exit__(self, type, value, traceback):
        with io.job(_("  {node}  removing hard lock...").format(node=self.node.name)):
            result = self.node.run("rm -R {}".format(quote(HARD_LOCK_PATH)), may_fail=True)

        if result.return_code != 0:
            io.stderr(_("{x} {node}  could not release hard lock").format(
                node=bold(self.node.name),
                x=red("!"),
            ))

    def _warning_message_hard(self, info):
        return wrap_question(
            red(_("NODE LOCKED")),
            _(
                "Looks like somebody is currently using BundleWrap on this node.\n"
                "You should let them finish or override the lock if it has gone stale.\n"
                "\n"
                "locked by  {user}\n"
                "    since  {date} ({duration} ago)"
            ).format(
                user=bold(info['user']),
                date=info['date'],
                duration=info['duration'],
            ),
            bold(_("Override lock?")),
            prefix="{x} {node} ".format(node=bold(self.node.name), x=blue("?")),
        )

    @cached_property
    def soft_locks(self):
        return softlock_list(self.node)

    @cached_property
    def my_soft_locks(self):
        for lock in self.soft_locks:
            if lock['user'] == identity():
                yield lock

    @cached_property
    def other_peoples_soft_locks(self):
        for lock in self.soft_locks:
            if lock['user'] != identity():
                yield lock


def softlock_add(node, lock_id, comment="", expiry="8h", item_selectors=None):
    if "\n" in comment:
        raise ValueError(_("Lock comments must not contain any newlines"))
    if not item_selectors:
        item_selectors = ["*"]

    expiry_timedelta = parse_duration(expiry)
    now = time()
    expiry_timestamp = now + expiry_timedelta.days * 86400 + expiry_timedelta.seconds

    content = json.dumps({
        'comment': comment,
        'date': now,
        'expiry': expiry_timestamp,
        'id': lock_id,
        'items': item_selectors,
        'user': identity(),
    }, indent=None, sort_keys=True)

    with tempfile() as local_path:
        with open(local_path, 'w') as f:
            f.write(content + "\n")
        node.run("mkdir -p " + quote(SOFT_LOCK_PATH))
        node.upload(local_path, SOFT_LOCK_FILE.format(id=lock_id), mode='0644')

    return lock_id


def softlock_list(node):
    with io.job(_("  {}  checking soft locks...").format(node.name)):
        cat = node.run("cat {}".format(SOFT_LOCK_FILE.format(id="*")), may_fail=True)
        if cat.return_code != 0:
            return []
        result = []
        for line in cat.stdout.decode('utf-8').strip().split("\n"):
            try:
                result.append(json.loads(line.strip()))
            except json.decoder.JSONDecodeError:
                io.stderr(_(
                    "{x} {node}  unable to parse soft lock file contents, ignoring: {line}"
                ).format(
                    x=red("!"),
                    node=bold(node.name),
                    line=line.strip(),
                ))
        for lock in result[:]:
            if lock['expiry'] < time():
                io.debug(_("removing expired soft lock {id} from node {node}").format(
                    id=lock['id'],
                    node=node.name,
                ))
                softlock_remove(node, lock['id'])
                result.remove(lock)
        return result


def softlock_remove(node, lock_id):
    io.debug(_("removing soft lock {id} from node {node}").format(
        id=lock_id,
        node=node.name,
    ))
    node.run("rm {}".format(SOFT_LOCK_FILE.format(id=lock_id)))
