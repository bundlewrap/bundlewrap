# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime, timedelta
from getpass import getuser
import json
from os import environ, remove
from pipes import quote
from socket import gethostname
from tempfile import mkstemp
from time import time

from . import operations
from .bundle import Bundle
from .concurrency import WorkerPool
from .deps import (
    find_item,
    prepare_dependencies,
)
from .exceptions import (
    ItemDependencyError,
    NodeAlreadyLockedException,
    NoSuchBundle,
    RepositoryError,
)
from .itemqueue import ItemQueue
from .items import Item
from .utils import cached_property, graph_for_items, merge_dict, names
from .utils.statedict import hash_statedict
from .utils.text import bold, green, red, validate_name, yellow
from .utils.text import force_text, mark_for_translation as _
from .utils.ui import io

LOCK_PATH = "/tmp/bundlewrap.lock"
LOCK_FILE = LOCK_PATH + "/info"


class ApplyResult(object):
    """
    Holds information about an apply run for a node.
    """
    def __init__(self, node, item_results):
        self.node_name = node.name
        self.correct = 0
        self.fixed = 0
        self.skipped = 0
        self.failed = 0
        self.profiling_info = []

        for item_id, result, time_elapsed in item_results:
            self.profiling_info.append((time_elapsed, item_id))
            if result == Item.STATUS_ACTION_SUCCEEDED:
                self.correct += 1
            elif result == Item.STATUS_OK:
                self.correct += 1
            elif result == Item.STATUS_FIXED:
                self.fixed += 1
            elif result == Item.STATUS_SKIPPED:
                self.skipped += 1
            elif result == Item.STATUS_FAILED:
                self.failed += 1
            else:
                raise RuntimeError(_(
                    "can't make sense of results for {} on {}: {}"
                ).format(item_id, self.node_name, result))

        self.profiling_info.sort()
        self.profiling_info.reverse()

        self.start = None
        self.end = None

    @property
    def duration(self):
        return self.end - self.start


def handle_apply_result(node, item, status_code, interactive, changes=None):
    formatted_result = format_item_result(
        status_code,
        node.name,
        item.bundle.name if item.bundle else "",  # dummy items don't have bundles
        item.id,
        interactive=interactive,
        changes=changes,
    )
    if formatted_result is not None:
        if status_code == Item.STATUS_FAILED:
            io.stderr(formatted_result)
        else:
            io.stdout(formatted_result)


def apply_items(node, workers=1, interactive=False, profiling=False):
    item_queue = ItemQueue(node.items)
    with WorkerPool(workers=workers) as worker_pool:
        # This whole thing is set in motion because every worker
        # initially asks for work. He also reports back when he finished
        # a job. Actually, all these conditions are internal to
        # worker_pool -- it will tell us whether we must keep going:
        while worker_pool.keep_running():
            msg = worker_pool.get_event()
            if msg['msg'] == 'REQUEST_WORK':
                try:
                    item, skipped_items = item_queue.pop()
                except IndexError:
                    if worker_pool.jobs_open > 0:
                        # No work right now, but another worker might
                        # finish and "create" a new job. Keep this
                        # worker idle.
                        worker_pool.mark_idle(msg['wid'])
                    else:
                        # No work, no outstanding jobs. We're done.
                        # quit() decreases workers_alive.
                        worker_pool.quit(msg['wid'])
                else:
                    for skipped_item in skipped_items:
                        handle_apply_result(node, skipped_item, Item.STATUS_SKIPPED, interactive)
                        yield(skipped_item.id, Item.STATUS_SKIPPED, timedelta(0))

                    # start_task() increases jobs_open.
                    worker_pool.start_task(
                        msg['wid'],
                        item.get_result if item.ITEM_TYPE_NAME == 'action' else item.apply,
                        task_id=item.id,
                        kwargs={'interactive': interactive},
                    )

            elif msg['msg'] == 'FINISHED_WORK':
                # worker_pool automatically decreases jobs_open when it
                # sees a 'FINISHED_WORK' message.

                # The task's id is the item we just processed.
                item_id = msg['task_id']
                item = find_item(item_id, item_queue.pending_items)

                status_code, changes = msg['return_value']

                if status_code == Item.STATUS_FAILED:
                    for skipped_item in item_queue.item_failed(item):
                        handle_apply_result(node, skipped_item, Item.STATUS_SKIPPED, interactive)
                        yield(skipped_item.id, Item.STATUS_SKIPPED, timedelta(0))
                elif status_code in (Item.STATUS_FIXED, Item.STATUS_ACTION_SUCCEEDED):
                    item_queue.item_fixed(item)
                elif status_code == Item.STATUS_OK:
                    item_queue.item_ok(item)
                elif status_code == Item.STATUS_SKIPPED:
                    for skipped_item in item_queue.item_skipped(item):
                        handle_apply_result(node, skipped_item, Item.STATUS_SKIPPED, interactive)
                        yield(skipped_item.id, Item.STATUS_SKIPPED, timedelta(0))
                else:
                    raise AssertionError(_(
                        "unknown item status return for {item}: {status}".format(
                            item=item.id,
                            status=repr(status_code),
                        ),
                    ))

                handle_apply_result(node, item, status_code, interactive, changes=changes)
                if item.ITEM_TYPE_NAME != 'dummy':
                    yield (item.id, status_code, msg['duration'])

                # Finally, we have a new job queue. Thus, tell all idle
                # workers to ask for work again.
                worker_pool.activate_idle_workers()

    # we have no items without deps left and none are processing
    # there must be a loop
    if item_queue.items_with_deps:
        io.debug(_(
            "There was a dependency problem. Look at the debug.svg generated "
            "by the following command and try to find a loop:\n"
            "echo '{}' | dot -Tsvg -odebug.svg"
        ).format("\\n".join(graph_for_items(node.name, item_queue.items_with_deps))))

        raise ItemDependencyError(
            _("bad dependencies between these items: {}").format(
                ", ".join([i.id for i in item_queue.items_with_deps]),
            )
        )


def _flatten_group_hierarchy(groups):
    """
    Takes a list of groups and returns a list of group names ordered so
    that parent groups will appear before any of their subgroups.
    """
    # dict mapping groups to subgroups
    child_groups = {}
    for group in groups:
        child_groups[group.name] = list(names(group.subgroups))

    # dict mapping groups to parent groups
    parent_groups = {}
    for child_group in child_groups.keys():
        parent_groups[child_group] = []
        for parent_group, subgroups in child_groups.items():
            if child_group in subgroups:
                parent_groups[child_group].append(parent_group)

    order = []

    while True:
        top_level_group = None
        for group, parents in parent_groups.items():
            if parents:
                continue
            else:
                top_level_group = group
                break
        if not top_level_group:
            if parent_groups:
                raise RuntimeError(
                    _("encountered subgroup loop that should have been detected")
                )
            else:
                break
        order.append(top_level_group)
        del parent_groups[top_level_group]
        for group in parent_groups.keys():
            if top_level_group in parent_groups[group]:
                parent_groups[group].remove(top_level_group)

    return order


def format_item_result(result, node, bundle, item, interactive=False, changes=None):
    # TODO use 'changes' (True when creating, False when deleting, list when editing)
    if result == Item.STATUS_FAILED:
        if interactive:
            return _("\n  {} {} failed").format(
                red("✘"),
                bold(item),
            )
        else:
            return "{node}:{bundle}:{item}: {status}".format(
                bundle=bundle,
                item=item,
                node=node,
                status=red(_("FAILED")),
            )
    elif result == Item.STATUS_ACTION_SUCCEEDED:
        if interactive:
            return _("\n  {} {} succeeded").format(
                green("✓"),
                bold(item),
            )
        else:
            return "{node}:{bundle}:{item}: {status}".format(
                bundle=bundle,
                item=item,
                node=node,
                status=green(_("SUCCEEDED")),
            )
    elif result == Item.STATUS_SKIPPED:
        if interactive:
            return _("\n  {} {} skipped").format(
                yellow("»"),
                bold(item),
            )
        else:
            return "{node}:{bundle}:{item}: {status}".format(
                bundle=bundle,
                item=item,
                node=node,
                status=yellow(_("SKIPPED")),
            )
    elif result == Item.STATUS_FIXED:
        if interactive:
            return _("\n  {} fixed {}").format(
                green("✓"),
                bold(item),
            )
        else:
            return "{node}:{bundle}:{item}: {status}".format(
                bundle=bundle,
                item=item,
                node=node,
                status=green(_("FIXED")),
            )


class Node(object):
    def __init__(self, name, infodict=None):
        if infodict is None:
            infodict = {}

        if not validate_name(name):
            raise RepositoryError(_("'{}' is not a valid node name").format(name))

        self.name = name
        self._bundles = infodict.get('bundles', [])
        self._node_metadata = infodict.get('metadata', {})
        self.add_ssh_host_keys = False
        self.hostname = infodict.get('hostname', self.name)
        self.use_shadow_passwords = infodict.get('use_shadow_passwords', True)

    def __lt__(self, other):
        return self.name < other.name

    def __repr__(self):
        return "<Node '{}'>".format(self.name)

    @cached_property
    def bundles(self):
        added_bundles = []
        found_bundles = []
        for group in self.groups:
            for bundle_name in group.bundle_names:
                found_bundles.append(bundle_name)

        for bundle_name in found_bundles + list(self._bundles):
            if bundle_name not in added_bundles:
                added_bundles.append(bundle_name)
                try:
                    yield Bundle(self, bundle_name)
                except NoSuchBundle:
                    raise NoSuchBundle(_(
                        "Node '{node}' wants bundle '{bundle}', but it doesn't exist."
                    ).format(
                        bundle=bundle_name,
                        node=self.name,
                    ))

    def cdict(self):
        node_dict = {}
        for item in self.items:
            try:
                node_dict[item.id] = item.hash()
            except AttributeError:  # actions have no cdict
                pass
        return node_dict

    @cached_property
    def groups(self):
        return self.repo.groups_for_node(self)

    def has_any_bundle(self, bundle_list):
        for bundle_name in bundle_list:
            if self.has_bundle(bundle_name):
                return True
        return False

    def has_bundle(self, bundle_name):
        for bundle in self.bundles:
            if bundle.name == bundle_name:
                return True
        return False

    def hash(self):
        return hash_statedict(self.cdict())

    def in_any_group(self, group_list):
        for group_name in group_list:
            if self.in_group(group_name):
                return True
        return False

    def in_group(self, group_name):
        for group in self.groups:
            if group.name == group_name:
                return True
        return False

    @property
    def items(self):
        for bundle in self.bundles:
            for item in bundle.items:
                yield item

    @property
    def _static_items(self):
        for bundle in self.bundles:
            for item in bundle._static_items:
                yield item

    def apply(self, interactive=False, force=False, workers=4, profiling=False):
        self.repo.hooks.node_apply_start(
            self.repo,
            self,
            interactive=interactive,
        )

        start = datetime.now()
        worker_count = 1 if interactive else workers
        try:
            with NodeLock(self, interactive, ignore=force):
                item_results = list(apply_items(
                    self,
                    workers=worker_count,
                    interactive=interactive,
                    profiling=profiling,
                ))
        except NodeAlreadyLockedException as e:
            if not interactive:
                io.error(_("Node '{node}' already locked: {info}").format(
                    node=self.name,
                    info=e.args,
                ))
            item_results = []
        result = ApplyResult(self, item_results)
        result.start = start
        result.end = datetime.now()

        self.repo.hooks.node_apply_end(
            self.repo,
            self,
            duration=result.duration,
            interactive=interactive,
            result=result,
        )

        return result

    def download(self, remote_path, local_path, ignore_failure=False):
        return operations.download(
            self.hostname,
            remote_path,
            local_path,
            add_host_keys=True if environ.get('BWADDHOSTKEYS', False) == "1" else False,
        )

    def get_item(self, item_id):
        return find_item(item_id, self.items)

    @cached_property
    def metadata(self):
        m = {}

        # step 1: group metadata
        group_order = _flatten_group_hierarchy(self.groups)
        for group_name in group_order:
            m = merge_dict(m, self.repo.get_group(group_name).metadata)

        # step 2: node metadata
        m = merge_dict(m, self._node_metadata)

        # step 3: metadata.py
        # TODO safeguard against endless loop
        while True:
            modified = False
            for metadata_processor in self.metadata_processors:
                processed = metadata_processor(m)
                if processed is not None:
                    m = processed
                    modified = True
            if not modified:
                break

        return m

    @property
    def metadata_processors(self):
        for bundle in self.bundles:
            for metadata_processor in bundle.metadata_processors:
                yield metadata_processor

    def run(self, command, may_fail=False, log_output=False):
        if log_output:
            def log_function(msg):
                io.stdout("[{}] {}".format(self.name, force_text(msg).rstrip("\n")))
        else:
            log_function = None
        return operations.run(
            self.hostname,
            command,
            ignore_failure=may_fail,
            add_host_keys=True if environ.get('BWADDHOSTKEYS', False) == "1" else False,
            log_function=log_function,
        )

    def test(self, workers=4):
        test_items(
            self.items,
            workers=workers,
        )

    def upload(self, local_path, remote_path, mode=None, owner="", group=""):
        return operations.upload(
            self.hostname,
            local_path,
            remote_path,
            mode=mode,
            owner=owner,
            group=group,
            add_host_keys=True if environ.get('BWADDHOSTKEYS', False) == "1" else False,
        )

    def verify(self, show_all=False, workers=4):
        bad = 0
        good = 0
        for item_status in verify_items(
            self.items,
            show_all=show_all,
            workers=workers,
        ):
            if item_status:
                good += 1
            else:
                bad += 1

        return {'good': good, 'bad': bad}


class NodeLock(object):
    def __init__(self, node, interactive, ignore=False):
        self.node = node
        self.ignore = ignore
        self.interactive = interactive

    def __enter__(self):
        handle, local_path = mkstemp()

        try:
            result = self.node.run("mkdir " + quote(LOCK_PATH), may_fail=True)
            if result.return_code != 0:
                self.node.download(LOCK_FILE, local_path, ignore_failure=True)
                with open(local_path, 'r') as f:
                    try:
                        info = json.loads(f.read())
                    except:
                        io.stderr(_("unable to read or parse lock file contents"))
                        info = {}
                if self.ignore or (self.interactive and io.ask(
                    self._warning_message(info),
                    False,
                )):
                    pass
                else:
                    raise NodeAlreadyLockedException(info)

            with open(local_path, 'w') as f:
                f.write(json.dumps({
                    'date': time(),
                    'user': getuser(),
                    'host': gethostname(),
                }))
            self.node.upload(local_path, LOCK_FILE)
        finally:
            remove(local_path)

    def __exit__(self, type, value, traceback):
        result = self.node.run("rm -R {}".format(quote(LOCK_PATH)), may_fail=True)

        if result.return_code != 0:
            io.stderr(_("Could not release lock for node '{node}'").format(
                node=self.node.name,
            ))

    def _warning_message(self, info):
        try:
            d = info['date']
            date = datetime.fromtimestamp(d).strftime("%c")
            duration = str(datetime.now() - datetime.fromtimestamp(d)).split(".")[0]
        except KeyError:
            date = _("<unknown>")
            duration = _("<unknown>")
        return _(
            "\n"
            "  {warning}\n\n"
            "  Looks like somebody is currently using BundleWrap on this node.\n"
            "  You should let them finish or override the lock if it has gone stale.\n\n"
            "  locked by: {user}@{host}\n"
            "  lock acquired: {duration} ago ({date})\n\n"
            "  Override lock?"
        ).format(
            warning=red(_("WARNING")),
            node=bold(self.node.name),
            user=bold(info.get('user', _("<unknown>"))),
            host=info.get('host', _("<unknown>")),
            date=date,
            duration=bold(duration),
        )


def test_items(items, workers=1):
    items = prepare_dependencies(items)

    with WorkerPool(workers=workers) as worker_pool:
        while worker_pool.keep_running():
            msg = worker_pool.get_event()
            if msg['msg'] == 'REQUEST_WORK':
                while True:
                    if items:
                        item = items.pop()
                        if item.ITEM_TYPE_NAME == 'dummy':
                            continue
                        worker_pool.start_task(
                            msg['wid'],
                            item.test,
                            task_id=item.node.name + ":" + item.id,
                        )
                        break
                    else:
                        worker_pool.quit(msg['wid'])
                        break
            elif msg['msg'] == 'FINISHED_WORK':
                item_id = msg['task_id']
                io.stdout("{} {}".format(
                    green("✓"),
                    item_id,
                ))


def verify_items(all_items, show_all=False, workers=1):
    items = []
    for item in all_items:
        if not item.ITEM_TYPE_NAME == 'action' and not item.triggered:
            items.append(item)

    with WorkerPool(workers=workers) as worker_pool:
        while worker_pool.keep_running():
            msg = worker_pool.get_event()
            if msg['msg'] == 'REQUEST_WORK':
                if items:
                    item = items.pop()
                    worker_pool.start_task(
                        msg['wid'],
                        item.get_status,
                        task_id=item.node.name + ":" + item.id,
                    )
                else:
                    worker_pool.quit(msg['wid'])
            elif msg['msg'] == 'FINISHED_WORK':
                item_id = msg['task_id']
                item_status = msg['return_value']
                if not item_status.correct:
                    io.stderr("{} {}".format(
                        red("✘"),
                        item_id,
                    ))
                    yield False
                else:
                    if show_all:
                        io.stdout("{} {}".format(
                            green("✓"),
                            item_id,
                        ))
                    yield True
