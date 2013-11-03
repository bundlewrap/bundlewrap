from datetime import datetime
from getpass import getuser
import json
from socket import gethostname
from tempfile import mkstemp
from time import time

from . import operations
from .bundle import Bundle
from .concurrency import WorkerPool
from .exceptions import ItemDependencyError, NodeAlreadyLockedException, \
                        RepositoryError
from .utils import cached_property, LOG
from .utils.text import mark_for_translation as _
from .utils.text import red, validate_name, white
from .utils.ui import ask_interactively, LineBuffer


class ApplyResult(object):
    """
    Holds information about an apply run for a node.
    """
    def __init__(self, node, item_results):
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
        self.item_type = item_type
        self._deps = []

    def __repr__(self):
        return "<DummyItem: {}>".format(self.item_type)

    @property
    def id(self):
        return "{}:".format(self.item_type)

    def apply(self, *args, **kwargs):
        return None


def inject_dummy_items(items):
    """
    Takes a list of items and adds dummy items depending on each type of
    item in the list. Returns the appended list.
    """
    # first, find all types of items and add dummy deps
    dummy_items = {}
    items = list(items)
    for item in items:
        # merge static and user-defined deps into a temporary attribute
        item._deps = item.DEPENDS_STATIC + item.depends

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


def apply_items(items, workers=1, interactive=False):
    items = inject_dummy_items(items)
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
                dep = worker.id
                result = worker.reap()
                # when we started the task (see below) we set
                # the worker id to the item id that we can now
                # remove from the dep lists
                items_with_deps, items_without_deps = \
                    split_items_without_deps(
                        remove_dep_from_items(
                            items_with_deps,
                            dep,
                        ) + items_without_deps
                    )
                if result is not None:  # ignore from dummy items
                    yield result

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
        worker_count = 1 if interactive else workers
        try:
            with NodeLock(self, interactive):
                item_results = list(apply_items(
                    self.items,
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
        result = ApplyResult(self, item_results)
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


class NodeLock(object):
    def __init__(self, node, interactive):
        self.node = node
        self.interactive = interactive

    def __enter__(self):
        handle, local_path = mkstemp()

        result = self.node.run("mkdir /tmp/bw.lock", may_fail=True)
        if result.return_code != 0:
            self.node.download("/tmp/bw.lock/info", local_path, ignore_failure=True)
            info = _("<no locking info found>")
            with open(local_path, 'r') as f:
                info = json.loads(f.read())
            if self.interactive and ask_interactively(_(
                "  {warning}\n\n"
                "  Looks like somebody is currently using Blockwart on this node.\n"
                "  You should let them finish or override the lock if it has gone stale.\n\n"
                "  locked by: {user}@{host}\n"
                "  lock acquired: {duration} ago ({date})\n\n"
                "  Override lock?").format(
                    warning=red(_("WARNING")),
                    node=white(self.node.name, bold=True),
                    user=white(info['user'], bold=True),
                    host=info['host'],
                    date=datetime.fromtimestamp(info['date']).strftime("%c"),
                    duration=white(str(
                        datetime.now() - datetime.fromtimestamp(info['date'])
                    ).split(".")[0], bold=True),
            ), False):
                pass
            else:
                raise NodeAlreadyLockedException(info)

        with open(local_path, 'w') as f:
            f.write(json.dumps({
                'date': time(),
                'user': getuser(),
                'host': gethostname()
            }))
        self.node.upload(local_path, "/tmp/bw.lock/info")

        # See issue #19. We've just opened an SSH connection to the node,
        # but before we can fork(), all connections *MUST* be closed!
        # XXX: Revise this once we're using Fabric 2.0.
        operations.disconnect_all()

    def __exit__(self, type, value, traceback):
        result = self.node.run("rm -R /tmp/bw.lock", may_fail=True)

        # See acquire_lock(). Most likely we won't fork() again now.
        # Nevertheless, clean up the state so a future code change won't
        # cause chaos.
        # XXX: Revise this once we're using Fabric 2.0.
        operations.disconnect_all()

        if result.return_code != 0:
            LOG.error(_("Could not release lock for {node}").format(node=self))
