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
from .exceptions import ItemDependencyError, NodeAlreadyLockedException, RepositoryError
from .items import ItemStatus
from .utils import cached_property, LOG
from .utils.text import mark_for_translation as _
from .utils.text import bold, green, red, validate_name
from .utils.ui import ask_interactively, LineBuffer

LOCK_PATH = "/tmp/blockwart.lock"
LOCK_FILE = LOCK_PATH + "/info"


class ApplyResult(object):
    """
    Holds information about an apply run for a node.
    """
    def __init__(self, node, item_results, action_results):
        self.node_name = node.name
        self.correct = 0
        self.fixed = 0
        self.aborted = 0
        self.unfixable = 0
        self.failed = 0
        for before, after in item_results:
            if before.correct and after.correct:
                self.correct += 1
            elif after.aborted:
                self.aborted += 1
            elif not before.fixable or not after.fixable:
                self.unfixable += 1
            elif not before.correct and after.correct:
                self.fixed += 1
            elif not before.correct and not after.correct:
                self.failed += 1
            else:
                raise RuntimeError(_(
                    "can't make sense of item results for node '{}'\n"
                    "before: {}\n"
                    "after: {}"
                ).format(self.node_name, before, after))

        self.actions_ok = 0
        self.actions_failed = 0
        self.actions_aborted = 0
        for result in action_results:
            if result is True:
                self.actions_ok += 1
            elif result is False:
                self.actions_failed += 1
            else:
                self.actions_aborted += 1

        self.start = None
        self.end = None

    @property
    def duration(self):
        return self.end - self.start


class DummyItem(object):
    """
    Represents a dependency on all items of a certain type.
    """
    def __init__(self, item_type):
        self.DEPENDS_STATIC = []
        self.depends = []
        self.item_type = item_type
        self._deps = []

    def __repr__(self):
        return "<DummyItem: {}>".format(self.item_type)

    @property
    def id(self):
        return "{}:".format(self.item_type)

    def apply(self, *args, **kwargs):
        return (None, None)


def _find_item(item_id, items):
    """
    Returns the first item with the given ID within the given list of
    items.
    """
    return filter(lambda item: item.id == item_id, items)[0]


def _find_items_of_type(item_type, items):
    """
    Returns a subset of items with the given type.
    """
    return filter(
        lambda item: item.id.startswith(item_type + ":"),
        items,
    )


def _get_deps_for_item(item, items, deps_found=None):
    """
    Recursively retrieves and returns a list of all inherited
    dependencies of the given item.

    Note: This can handle loops, but won't detect them.
    """
    if deps_found is None:
        deps_found = []
    deps = []
    for dep in item._deps:
        if dep not in deps_found:
            deps.append(dep)
            deps_found.append(dep)
            deps += _get_deps_for_item(
                _find_item(dep, items),
                items,
                deps_found,
            )
    return deps


def flatten_dependencies(items):
    """
    This will cause all dependencies - direct AND inherited - to be
    listed in item._deps.
    """
    for item in items:
        item._flattened_deps = list(set(
            item._deps + _get_deps_for_item(item, items)
        ))
    return items


def inject_dummy_items(items):
    """
    Takes a list of items and adds dummy items depending on each type of
    item in the list. Returns the appended list.
    """
    # first, find all types of items and add dummy deps
    dummy_items = {}
    items = list(items)
    for item in items:
        # create dummy items that depend on each item of their type
        item_type = item.id.split(":")[0]
        if item_type not in dummy_items:
            dummy_items[item_type] = DummyItem(item_type)
        dummy_items[item_type]._deps.append(item.id)

        # create DummyItem for every type
        for dep in item._deps:
            item_type = dep.split(":")[0]
            if item_type not in dummy_items:
                dummy_items[item_type] = DummyItem(item_type)
    return list(dummy_items.values()) + items


def inject_concurrency_blockers(items):
    """
    Looks for items with PARALLEL_APPLY set to False and inserts
    dependencies to force a sequential apply.
    """
    # find every item type that cannot be applied in parallel
    item_types = []
    for item in items:
        if (
            isinstance(item, DummyItem) or
            item.PARALLEL_APPLY or
            item.ITEM_TYPE_NAME in item_types
        ):
            continue
        else:
            item_types.append(item.ITEM_TYPE_NAME)

    # daisy-chain all other items of the same type (linked list style)
    # while respecting existing inter-item dependencies
    for item_type in item_types:
        type_items = _find_items_of_type(item_type, items)
        processed_items = []
        for item in type_items:
            # disregard deps to items of other types
            item.__deps = filter(
                lambda dep: dep.startswith(item_type + ":"),
                item._flattened_deps,
            )
        previous_item = None
        while len(processed_items) < len(type_items):
            # find the first item without same-type deps we haven't
            # processed yet
            item = filter(
                lambda item: not item.__deps and item not in processed_items,
                type_items,
            )[0]
            if previous_item is not None:  # unless we're at the first item
                # add dep to previous item -- unless it's already in there
                if not previous_item.id in item._deps:
                    item._deps.append(previous_item.id)
            previous_item = item
            processed_items.append(item)
            for other_item in type_items:
                try:
                    other_item.__deps.remove(item.id)
                except ValueError:
                    pass
    return items


def apply_items(items, workers=1, interactive=False):
    # make sure items is not a generator
    items = list(items)

    for item in items:
        # merge static and user-defined deps
        item._deps = list(item.DEPENDS_STATIC)
        item._deps += item.depends

    items = inject_dummy_items(items)
    items = flatten_dependencies(items)
    items = inject_concurrency_blockers(items)

    with WorkerPool(workers=workers) as worker_pool:
        items_with_deps, items_without_deps = \
            split_items_without_deps(items)
        # there are three things we want to do continuously:
        # 1) process items without deps as long as we have free workers
        # 2) get results from finished ("reapable") workers
        # 3) if there is nothing else to do, wait for a worker to finish
        while (
            items_without_deps or
            worker_pool.busy_count > 0 or
            worker_pool.reapable_count > 0
        ):
            while items_without_deps:
                # 1
                worker = worker_pool.get_idle_worker(block=False)
                if worker is None:
                    break
                item = items_without_deps.pop()
                worker.start_task(
                    item.apply,
                    id=item.id,
                    kwargs={'interactive': interactive},
                )

            while worker_pool.reapable_count > 0:
                # 2
                worker = worker_pool.get_reapable_worker()
                # when we started the task (see above) we set
                # the worker id to the item id
                dep = worker.id
                status_before, status_after = worker.reap()

                if (
                    status_before is None or
                    status_before.correct or
                    status_after.aborted or
                    not interactive
                ):
                    pass
                elif status_after.correct:
                    print(_("\n  {} fixed {}").format(
                        green("✓"),
                        bold(dep),
                    ))
                else:
                    print(_("\n  {} failed to fix {}").format(
                        red("✘"),
                        bold(dep),
                    ))

                if status_after is not None and not status_after.correct:
                    # if an item fails or is aborted, all items that depend on
                    # it shall be removed from the queue
                    items_with_deps, cancelled_items = remove_item_dependents(
                        items_with_deps,
                        dep,
                    )
                    # since we removed them from further processing, we
                    # fake the status of the removed items so they still
                    # show up in the result statistics
                    for cancelled_item in cancelled_items:
                        if isinstance(cancelled_item, DummyItem):
                            continue
                        cancelled_item_status = ItemStatus(correct=False)
                        cancelled_item_status.aborted = True
                        yield (cancelled_item_status, cancelled_item_status)
                else:
                    # if an item is applied successfully, all
                    # dependencies on it can be removed from the
                    # remaining items
                    items_with_deps = remove_dep_from_items(
                        items_with_deps,
                        dep,
                    )

                # now that we removed some deps from items_with_deps, we
                # again need to look for items that don't have any deps
                # left and can be processed next
                items_with_deps, items_without_deps = \
                    split_items_without_deps(items_with_deps + items_without_deps)

                if not (status_before is None and status_after is None):
                    #   ^- ignore from dummy items
                    yield (status_before, status_after)

            if (
                worker_pool.busy_count > 0 and
                not items_without_deps and
                not worker_pool.reapable_count
            ):
                # 3
                worker_pool.wait()

    # we have no items without deps left and none are processing
    # there must be a loop
    if items_with_deps:
        raise ItemDependencyError(
            _("bad dependencies between these items: {}").format(
                ", ".join([repr(i) for i in items_with_deps]),
            )
        )


def split_items_without_deps(items):
    """
    Takes a list of items and extracts the ones that don't have any
    dependencies. The extracted deps are returned as a list.
    """
    items = list(items)  # make sure we're not returning a generator
    removed_items = []
    for item in items:
        if not item._deps:
            removed_items.append(item)
    for item in removed_items:
        items.remove(item)
    return (items, removed_items)


def remove_dep_from_items(items, dep):
    """
    Removes the given item id (dep) from the temporary list of
    dependencies of all items in the given list.
    """
    for item in items:
        try:
            item._deps.remove(dep)
        except ValueError:
            pass
    return items


def remove_item_dependents(items, dep):
    """
    Removes the items depending on the given id from the list of items.
    """
    removed_items = []
    for item in items:
        # remove failed item from static and concurrency blocker deps
        try:
            item._deps.remove(dep)
        except ValueError:
            pass
        # only cascade item abort if it was an explicit dep
        if dep in item.depends:
            items.remove(item)
            removed_items.append(item)

    if removed_items:
        LOG.debug(
            "aborted these items because they depend on {}, which was "
            "aborted previously: {}".format(
                dep,
                ", ".join([item.id for item in removed_items]),
            )
        )

    all_recursively_removed_items = []
    for removed_item in removed_items:
        items, recursively_removed_items = \
            remove_item_dependents(items, removed_item.id)
        all_recursively_removed_items += recursively_removed_items

    return (items, removed_items + all_recursively_removed_items)


def run_actions(actions, timing, workers=1, interactive=False):
    # filter actions with wrong timing
    actions = [action for action in actions if action.timing == timing]

    with WorkerPool(workers=workers) as worker_pool:
        while (
            actions or
            worker_pool.busy_count > 0 or
            worker_pool.reapable_count > 0
        ):
            while actions:
                worker = worker_pool.get_idle_worker(block=False)
                if worker is None:
                    break
                action = actions.pop()
                worker.start_task(
                    action.get_result,
                    id=action.name,
                    kwargs={'interactive': interactive},
                )

            while worker_pool.reapable_count > 0:
                worker = worker_pool.get_reapable_worker()
                action_name = worker.id
                result = worker.reap()
                if interactive:
                    if result is False:
                        print(_("\n  {} action:{} failed").format(
                            red("✘"),
                            bold(action_name),
                        ))
                    elif result is True:
                        print(_("\n  {} action:{} succeeded").format(
                            green("✓"),
                            bold(action_name),
                        ))
                yield result

            if (
                worker_pool.busy_count > 0 and
                not actions and
                not worker_pool.reapable_count
            ):
                worker_pool.wait()


def verify_items(items, workers=1):
    # make sure items is not a generator
    items = list(items)

    with WorkerPool(workers=workers) as worker_pool:
        while (
            items or
            worker_pool.busy_count > 0 or
            worker_pool.reapable_count > 0
        ):
            while items:
                worker = worker_pool.get_idle_worker(block=False)
                if worker is None:
                    break
                item = items.pop()
                worker.start_task(
                    item.get_status,
                    id=item.node.name + ":" + item.id,
                )

            while worker_pool.reapable_count > 0:
                worker = worker_pool.get_reapable_worker()
                item_id = worker.id
                item_status = worker.reap()
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

            if (
                worker_pool.busy_count > 0 and
                not items and
                not worker_pool.reapable_count
            ):
                worker_pool.wait()


class Node(object):
    def __init__(self, repo, name, infodict=None):
        if infodict is None:
            infodict = {}

        if not validate_name(name):
            raise RepositoryError(_("'{}' is not a valid node name"))

        self.name = name
        self.repo = repo
        self.hostname = infodict.get('hostname', self.name)
        self.metadata = infodict.get('metadata', {})
        self.use_shadow_passwords = infodict.get('use_shadow_passwords', True)

    def __cmp__(self, other):
        return cmp(self.name, other.name)

    def __repr__(self):
        return "<Node '{}'>".format(self.name)

    @property
    def actions(self):
        for bundle in self.bundles:
            for action in bundle.actions:
                yield action

    @cached_property
    def bundles(self):
        for group in self.groups:
            for bundle_name in group.bundle_names:
                yield Bundle(self, bundle_name)

    @cached_property
    def groups(self):
        return self.repo.groups_for_node(self)

    @property
    def items(self):
        for bundle in self.bundles:
            for item in bundle.items:
                yield item

    def apply(self, interactive=False, workers=4):
        start = datetime.now()
        action_results = []
        worker_count = 1 if interactive else workers
        try:
            with NodeLock(self, interactive):
                action_results += list(run_actions(
                    self.actions,
                    'pre',
                    workers=worker_count,
                    interactive=interactive,
                ))

                item_results = list(apply_items(
                    self.items,
                    workers=worker_count,
                    interactive=interactive,
                ))

                action_results += list(run_actions(
                    self.actions,
                    'post',
                    workers=worker_count,
                    interactive=interactive,
                ))

        except NodeAlreadyLockedException as e:
            if not interactive:
                LOG.error(_("Node '{node}' already locked: {info}").format(
                    node=self.name,
                    info=e.args,
                ))
            item_results = []
        result = ApplyResult(self, item_results, action_results)
        result.start = start
        result.end = datetime.now()
        return result

    def download(self, remote_path, local_path, ignore_failure=False):
        return operations.download(
            self.hostname,
            remote_path,
            local_path,
            ignore_failure=ignore_failure,
        )

    def run(self, command, may_fail=False, pty=False, stderr=None, stdout=None,
            sudo=True):
        if stderr is None:
            stderr = LineBuffer(lambda s: None)
        if stdout is None:
            stdout = LineBuffer(lambda s: None)
        return operations.run(
            self.hostname,
            command,
            ignore_failure=may_fail,
            stderr=stderr,
            stdout=stdout,
            sudo=sudo,
            pty=pty,
        )

    def upload(self, local_path, remote_path):
        return operations.upload(
            self.hostname,
            local_path,
            remote_path,
        )

    def verify(self, workers=4):
        verify_items(
            self.items,
            workers=workers,
        )


class NodeLock(object):
    def __init__(self, node, interactive):
        self.node = node
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
            if self.interactive and ask_interactively(
                self._warning_message(info),
                False,
            ):
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
            "  Looks like somebody is currently using Blockwart on this node.\n"
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
