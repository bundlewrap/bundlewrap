# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
from getpass import getuser
import json
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
    remove_item_dependents,
    remove_dep_from_items,
    split_items_without_deps,
)
from .exceptions import (
    ItemDependencyError,
    NodeAlreadyLockedException,
    NoSuchBundle,
    NoSuchItem,
    RepositoryError,
)
from .items import Item
from .utils import cached_property, LOG, graph_for_items, names
from .utils.text import mark_for_translation as _
from .utils.text import bold, green, red, validate_name, yellow
from .utils.ui import ask_interactively

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


def apply_items(node, workers=1, interactive=False, profiling=False):
    items = prepare_dependencies(node.items)

    with WorkerPool(workers=workers) as worker_pool:
        items_with_deps, items_without_deps = \
            split_items_without_deps(items)

        # This whole thing is set in motion because every worker
        # initially asks for work. He also reports back when he finished
        # a job. Actually, all these conditions are internal to
        # worker_pool -- it will tell us whether we must keep going:
        while worker_pool.keep_running():
            msg = worker_pool.get_event()

            if msg['msg'] == 'REQUEST_WORK':
                if items_without_deps:
                    # There's work! Do it.
                    item = items_without_deps.pop()

                    if item.ITEM_TYPE_NAME == 'action':
                        target = item.get_result
                    else:
                        target = item.apply

                    # start_task() increases jobs_open.
                    worker_pool.start_task(
                        msg['wid'],
                        target,
                        task_id=item.id,
                        kwargs={'interactive': interactive},
                    )
                else:
                    if worker_pool.jobs_open > 0:
                        # No work right now, but another worker might
                        # finish and "create" a new job. Keep this
                        # worker idle.
                        worker_pool.mark_idle(msg['wid'])
                    else:
                        # No work, no outstanding jobs. We're done.
                        # quit() decreases workers_alive.
                        worker_pool.quit(msg['wid'])

            elif msg['msg'] == 'FINISHED_WORK':
                # worker_pool automatically decreases jobs_open when it
                # sees a 'FINISHED_WORK' message.

                # The task's id is the item we just processed.
                item_id = msg['task_id']
                item = find_item(item_id, items)

                status_code = msg['return_value']

                formatted_result = format_item_result(
                    status_code,
                    node.name,
                    item.bundle.name if item.bundle else "",  # dummy items don't have bundles
                    item.id,
                    interactive=interactive,
                )
                if formatted_result is not None:
                    if interactive:
                        print(formatted_result)
                    else:
                        if status_code == Item.STATUS_FAILED:
                            LOG.error(formatted_result)
                        else:
                            LOG.info(formatted_result)

                if status_code in (
                    Item.STATUS_FAILED,
                    Item.STATUS_SKIPPED,
                ) and item.cascade_skip:
                    # if an item fails or is skipped, all items that depend on
                    # it shall be removed from the queue
                    items_with_deps, skipped_items = remove_item_dependents(
                        items_with_deps,
                        item.id,
                    )
                    # since we removed them from further processing, we
                    # fake the status of the removed items so they still
                    # show up in the result statistics
                    for skipped_item in skipped_items:
                        if skipped_item.ITEM_TYPE_NAME == 'dummy':
                            continue
                        formatted_result = format_item_result(
                            Item.STATUS_SKIPPED,
                            node.name,
                            skipped_item.bundle.name,
                            skipped_item.id,
                            interactive=interactive,
                        )
                        if interactive:
                            print(formatted_result)
                        else:
                            LOG.info(formatted_result)
                        yield (skipped_item.id, Item.STATUS_SKIPPED, msg['duration'])
                else:
                    # if an item is applied successfully, all
                    # dependencies on it can be removed from the
                    # remaining items
                    items_with_deps = remove_dep_from_items(
                        items_with_deps,
                        item.id,
                    )

                # now that we removed some deps from items_with_deps, we
                # again need to look for items that don't have any deps
                # left and can be processed next
                items_with_deps, items_without_deps = \
                    split_items_without_deps(items_with_deps + items_without_deps)

                if status_code in (Item.STATUS_FIXED, Item.STATUS_ACTION_SUCCEEDED) or (
                    status_code == Item.STATUS_SKIPPED and
                    not item.cascade_skip
                ):
                    # action succeeded or item was fixed
                    for triggered_item_id in item.triggers:
                        try:
                            triggered_item = find_item(
                                triggered_item_id,
                                items_with_deps + items_without_deps,
                            )
                            triggered_item.has_been_triggered = True
                        except NoSuchItem:
                            LOG.debug(_(
                                "{item} tried to trigger {triggered_item}, "
                                "but it wasn't available. It must have been skipped previously."
                            ).format(
                                item=item.id,
                                triggered_item=triggered_item_id,
                            ))

                if item.ITEM_TYPE_NAME != 'dummy':
                    yield (item.id, status_code, msg['duration'])

                # Finally, we have a new job queue. Thus, tell all idle
                # workers to ask for work again.
                worker_pool.activate_idle_workers()

    # we have no items without deps left and none are processing
    # there must be a loop
    if items_with_deps:
        LOG.debug(_(
            "There was a dependency problem. Look at the debug.svg generated "
            "by the following command and try to find a loop:\n"
            "echo '{}' | dot -Tsvg -odebug.svg"
        ).format("\\n".join(graph_for_items(node.name, items_with_deps))))

        raise ItemDependencyError(
            _("bad dependencies between these items: {}").format(
                ", ".join([i.id for i in items_with_deps]),
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


def format_item_result(result, node, bundle, item, interactive=False):
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
        self.hostname = infodict.get('hostname', self.name)
        self._node_metadata = infodict.get('metadata', {})
        self._password = infodict.get('password', None)
        self.use_shadow_passwords = infodict.get('use_shadow_passwords', True)

    def __cmp__(self, other):
        return cmp(self.name, other.name)

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
                LOG.error(_("Node '{node}' already locked: {info}").format(
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
            ignore_failure=ignore_failure,
            password=self.password,
        )

    def get_item(self, item_id):
        return find_item(item_id, self.items)

    @cached_property
    def metadata(self):
        m = {}
        group_order = _flatten_group_hierarchy(self.groups)
        for group_name in group_order:
            m.update(self.repo.get_group(group_name).metadata)
        m.update(self._node_metadata)
        for group_name in group_order:
            group = self.repo.get_group(group_name)
            for metadata_processor in group.metadata_processors:
                m = metadata_processor(self.name, group_order, m)
        return m

    @property
    def password(self):
        if self._password:
            return self._password
        elif not hasattr(self, "repo"):
            # in-memory nodes might not be attached to a repo
            return None
        elif self._password_from_groups:
            return self._password_from_groups
        else:
            return self.repo.password

    @password.setter
    def password(self, value):
        self._password = value

    @property
    def _password_from_groups(self):
        pwd = None
        group_order = _flatten_group_hierarchy(self.groups)
        for group_name in group_order:
            group = self.repo.get_group(group_name)
            if group.password:
                pwd = group.password
        return pwd

    def run(self, command, may_fail=False, pty=False, stderr=None, stdout=None,
            sudo=True):
        return operations.run(
            self.hostname,
            command,
            ignore_failure=may_fail,
            stderr=stderr,
            stdout=stdout,
            sudo=sudo,
            password=self.password,
            pty=pty,
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
            password=self.password,
        )

    def verify(self, workers=4):
        verify_items(
            self.items,
            workers=workers,
        )


class NodeLock(object):
    def __init__(self, node, interactive, ignore=False):
        self.node = node
        self.ignore = ignore
        self.interactive = interactive

    def __enter__(self):
        handle, local_path = mkstemp()

        result = self.node.run("mkdir " + quote(LOCK_PATH), may_fail=True)
        if result.return_code != 0:
            self.node.download(LOCK_FILE, local_path, ignore_failure=True)
            with open(local_path, 'r') as f:
                try:
                    info = json.loads(f.read())
                except:
                    LOG.warn(_("unable to read or parse lock file contents"))
                    info = {}
            if self.ignore or (self.interactive and ask_interactively(
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

        # See issue #19. We've just opened an SSH connection to the node,
        # but before we can fork(), all connections *MUST* be closed!
        # XXX: Revise this once we're using Fabric 2.0.
        operations.disconnect_all()

    def __exit__(self, type, value, traceback):
        result = self.node.run("rm -R {}".format(quote(LOCK_PATH)), may_fail=True)

        # See __enter__(). Most likely we won't fork() again now.
        # Nevertheless, clean up the state so a future code change won't
        # cause chaos.
        # XXX: Revise this once we're using Fabric 2.0.
        operations.disconnect_all()

        if result.return_code != 0:
            LOG.error(_("Could not release lock for node '{node}'").format(
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
                LOG.info("{} {}".format(
                    green("✓"),
                    item_id,
                ))


def verify_items(items_with_actions, workers=1):
    items = []
    for item in items_with_actions:
        if not item.ITEM_TYPE_NAME == 'action':
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
                    LOG.warning("{} {}".format(
                        red("✘"),
                        item_id,
                    ))
                else:
                    LOG.info("{} {}".format(
                        green("✓"),
                        item_id,
                    ))
