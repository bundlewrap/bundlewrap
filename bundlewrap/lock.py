from datetime import datetime
from getpass import getuser
import json
from os import environ
from shlex import quote
from socket import gethostname
from time import time

from .exceptions import (
    NodeLockedException,
    NoSuchNode,
    RemoteException,
    TransportException,
)
from .utils import cached_property, tempfile
from .utils.table import ROW_SEPARATOR, render_table
from .utils.text import (
    blue,
    bold,
    format_duration,
    format_timestamp,
    green,
    mark_for_translation as _,
    parse_duration,
    red,
    wrap_question,
    yellow,
)
from .utils.ui import io


def identity():
    return environ.get('BW_IDENTITY', "{}@{}".format(
        getuser(),
        gethostname(),
    ))


class NodeLock:
    def __init__(self, node, interactive=False, ignore=False):
        self.node = node
        self.ignore = ignore
        self.interactive = interactive
        self.locking_node = _get_locking_node(node)

    def __enter__(self):
        if self.locking_node.os not in self.locking_node.OS_FAMILY_UNIX:
            # no locking required/possible
            return self
        with tempfile() as local_path:
            self.locking_node.run("mkdir -p " + quote(self.locking_node.lock_dir))
            if not self.ignore:
                with io.job(_("{node}  checking hard lock status").format(node=bold(self.node.name))):
                    result = self.locking_node.run("mkdir " + quote(self._hard_lock_dir()), may_fail=True)
                    if result.return_code != 0:
                        info = self._get_hard_lock_info(local_path)
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

            with io.job(_("{node}  uploading lock file").format(node=bold(self.node.name))):
                if self.ignore:
                    self.locking_node.run("mkdir -p " + quote(self._hard_lock_dir()))
                with open(local_path, 'w') as f:
                    f.write(json.dumps({
                        'date': time(),
                        'user': identity(),
                    }))
                self.locking_node.upload(local_path, self._hard_lock_file())

        return self

    def __exit__(self, type, value, traceback):
        if self.locking_node.os not in self.locking_node.OS_FAMILY_UNIX:
            # no locking required/possible
            return
        with io.job(_("{node}  removing hard lock").format(node=bold(self.node.name))):
            result = self.locking_node.run("rm -R {}".format(quote(self._hard_lock_dir())), may_fail=True)

        if result.return_code != 0:
            io.stderr(_("{x} {node}  could not release hard lock").format(
                node=bold(self.node.name),
                x=red("!"),
            ))

    def _get_hard_lock_info(self, local_path):
        try:
            self.locking_node.download(self._hard_lock_file(), local_path)
            with open(local_path, 'r') as fp:
                return json.load(fp)
        except (RemoteException, TransportException, ValueError):
                io.stderr(_(
                    "{x} {node_bold}  corrupted hard lock: "
                    "unable to read or parse lock file contents "
                    "(clear it with `bw run {node} 'rm -Rf {path}'`)"
                ).format(
                    node_bold=bold(self.locking_node.name),
                    node=self.locking_node.name,
                    path=self._hard_lock_dir(),
                    x=red("!"),
                ))
                return {}

    def _hard_lock_dir(self):
        return self.locking_node.lock_dir + "/hard-" + quote(self.node.name)

    def _hard_lock_file(self):
        return self._hard_lock_dir() + "/info"

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


def _get_locking_node(node):
    if node.locking_node is not None:
        try:
            return node.repo.get_node(node.locking_node)
        except NoSuchNode:
            raise Exception("Invalid locking_node {} for {}".format(
                node.locking_node,
                node.name,
            ))
    else:
        return node


def _soft_lock_dir(node_name, locking_node):
    return locking_node.lock_dir + "/soft-" + quote(node_name)


def _soft_lock_file(node_name, locking_node, lock_id):
    return _soft_lock_dir(node_name, locking_node) + "/" + lock_id


def softlock_add(node, lock_id, comment="", expiry="8h", item_selectors=None):
    locking_node = _get_locking_node(node)
    assert locking_node.os in locking_node.OS_FAMILY_UNIX
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
        locking_node.run("mkdir -p " + quote(_soft_lock_dir(node.name, locking_node)))
        locking_node.upload(local_path, _soft_lock_file(node.name, locking_node, lock_id), mode='0644')

    node.repo.hooks.lock_add(node.repo, node, lock_id, item_selectors, expiry_timestamp, comment)

    return lock_id


def softlock_add_and_warn_for_others(node, *args, **kwargs):
    new_lock_id = softlock_add(node, *args, **kwargs)

    other_peoples_soft_locks = {node.name: []}
    for lock in softlock_list(node):
        if lock['user'] != identity():
            other_peoples_soft_locks[node.name].append(lock)

    if other_peoples_soft_locks[node.name]:
        output, _ignore = softlocks_to_table(other_peoples_soft_locks)

        io.stdout(_("{x}").format(x=yellow("!")))
        io.stdout(_(
            "{x} {node}  Your lock was added, but the node was already locked by other people:"
        ).format(
            x=yellow("!"),
            node=bold(node.name),
        ))
        io.stdout(_("{x}").format(x=yellow("!")))

        # TODO 5.0 Just use "page_lines(output)" here
        # For backwards compatibility, we don't use a pager, because
        # this might break people's workflows/scripts.
        for line in output:
            io.stdout(line)

    return new_lock_id


def softlock_list(node):
    locking_node = _get_locking_node(node)
    if locking_node.os not in locking_node.OS_FAMILY_UNIX:
        return []
    with io.job(_("{}  checking soft locks").format(bold(node.name))):
        cat = locking_node.run("cat {}".format(_soft_lock_file(node.name, locking_node, "*")), may_fail=True)
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
    locking_node = _get_locking_node(node)
    assert locking_node.os in locking_node.OS_FAMILY_UNIX
    io.debug(_("removing soft lock {id} from node {node}").format(
        id=lock_id,
        node=node.name,
    ))
    locking_node.run("rm {}".format(_soft_lock_file(node.name, locking_node, lock_id)))
    node.repo.hooks.lock_remove(node.repo, node, lock_id)


def softlocks_to_table(locks_on_node, items=None, repo=None, hide_nodes_without_locks=False):
    rows = [[
        bold(_("node")),
        bold(_("ID")),
        bold(_("created")),
        bold(_("expires")),
        bold(_("user")),
        bold(_("items")),
        bold(_("comment")),
    ], ROW_SEPARATOR]

    for node_name, locks in sorted(locks_on_node.items()):
        if locks:
            first_lock = True
            for lock in locks:
                lock['formatted_date'] = format_timestamp(lock['date'])
                lock['formatted_expiry'] = format_timestamp(lock['expiry'])
                first_item = True
                for item in lock['items']:
                    rows.append([
                        node_name if first_item and first_lock else "",
                        lock['id'] if first_item else "",
                        lock['formatted_date'] if first_item else "",
                        lock['formatted_expiry'] if first_item else "",
                        lock['user'] if first_item else "",
                        item,
                        lock['comment'] if first_item else "",
                    ])
                    # always repeat for grep style
                    first_item = environ.get("BW_TABLE_STYLE") == 'grep'
                # always repeat for grep style
                first_lock = environ.get("BW_TABLE_STYLE") == 'grep'
            rows.append(ROW_SEPARATOR)
        else:
            if not hide_nodes_without_locks:
                rows.append([
                    node_name,
                    _("(none)"),
                    "",
                    "",
                    "",
                    "",
                    "",
                ])
                rows.append(ROW_SEPARATOR)

    output = list(render_table(
        rows[:-1],  # remove trailing ROW_SEPARATOR
        alignments={1: 'center'},
    ))

    some_selected_items_locked = False

    if items:
        rows = [[
            bold(_("node")),
            bold(_("item")),
            bold(_("locked")),
            bold(_("ID")),
        ], ROW_SEPARATOR]
        for node_name, locks in sorted(locks_on_node.items()):
            node = repo.get_node(node_name)
            for item in sorted(node.items):
                if not item.covered_by_autoskip_selector(items):
                    continue
                locked_by = None
                for lock in locks:
                    if item.covered_by_autoskip_selector(lock['items']):
                        locked_by = lock['id']
                        some_selected_items_locked = True
                        break
                rows.append([
                    node.name,
                    item.id,
                    red(_("YES")) if locked_by else green(_("NO")),
                    locked_by or "",
                ])
            if rows[-1] != ROW_SEPARATOR:
                rows.append(ROW_SEPARATOR)

        output += list(render_table(
            rows[:-1],  # remove trailing ROW_SEPARATOR
        ))

    return output, some_selected_items_locked
