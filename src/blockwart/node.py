from paramiko.client import SSHClient, WarningPolicy
from time import sleep

from .bundle import Bundle
from .concurrency import WorkerPool
from .exceptions import ItemDependencyError, RepositoryError
from .utils import cached_property, mark_for_translation as _, validate_name


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


def apply_items_parallelly(items, workers):
    # noninteractive operation allows us to process multiple
    # nodes and items in parallel, which is somewhat more
    # involved than the linear order
    workers = WorkerPool(workers=workers)
    items_with_deps, items_without_deps = \
        split_items_without_deps(items)
    # there are three things we want to do continuously:
    # 1) process items without deps as long as we have free workers
    # 2) get results from finished ("reapable") workers
    # 3) if there is nothing else to do, wait for a worker to finish
    while (
        items_without_deps or
        workers.busy_count > 0 or
        workers.reapable_count > 0
    ):
        while items_without_deps:
            # 1
            worker = workers.get_idle_worker(block=False)
            if worker is None:
                break
            item = items_without_deps.pop()
            worker.start_task(item.apply, id=item.id)

        while workers.reapable_count > 0:
            # 2
            worker = workers.get_reapable_worker()
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
                    )
                )
            yield result

        if (
            workers.busy_count > 0 and
            not items_without_deps and
            not workers.reapable_count
        ):
            # 3
            sleep(.01)

    # we have no items without deps left and none are processing
    # there must be a loop
    if items_with_deps:
        raise ItemDependencyError(
            _("bad dependencies between these items: {}").format(
                ", ".join([repr(i) for i in items_with_deps]),
            )
        )


def apply_items_serially(items, interactive=True):
    for item in order_items(items):
        yield item.apply(interactive=interactive)


def inject_dummy_items(items):
    """
    Takes a list of items and adds dummy items depending on each type of
    item in the list. Returns the appended list.
    """
    # first, find all types of items and add dummy deps
    dummy_items = {}
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


def order_items(unordered_items):
    """
    Takes a list of items and returns them in an order that honors
    dependencies.

    Raises ItemDependencyError if there is a problem (e.g. dependency
    loop).
    """
    unordered_items = inject_dummy_items(unordered_items)

    # find items without deps to start with
    withdeps, nodeps = split_items_without_deps(unordered_items)

    ordered_items = []

    while nodeps:
        item = nodeps.pop()
        if not isinstance(item, DummyItem):
            # item without pending deps can be added to exec order
            # this is only done for non-dummy items
            # dummy items are not needed beyond this point
            ordered_items.append(item)

        # consider this item a satisfied dependency
        withdeps = remove_dep_from_items(withdeps, item.id)
        # update lists of items with and without deps
        withdeps, nodeps_new = split_items_without_deps(withdeps)
        nodeps += nodeps_new

    if withdeps:
        raise ItemDependencyError(
            _("bad dependencies between these items: {}").format(
                ", ".join([repr(i) for i in withdeps]),
            ),
        )

    return ordered_items


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


class RunResult(object):
    def __init__(self):
        self.returncode = None
        self.stderr = None
        self.stdout = None

    def __str__(self):
        return self.stdout


class Node(object):
    def __init__(self, repo, name, infodict=None):
        if infodict is None:
            infodict = {}

        if not validate_name(name):
            raise RepositoryError(_("'{}' is not a valid node name"))

        self.name = name
        self.repo = repo
        self.hostname = infodict.get('hostname', self.name)

    def __cmp__(self, other):
        return cmp(self.name, other.name)

    def __repr__(self):
        return "<Node '{}'>".format(self.name)

    @cached_property
    def _ssh_client(self):
        client = SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(WarningPolicy())
        client.connect(self.hostname)
        return client

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
        if interactive:
            apply_items_serially(self.items, interactive=interactive)
        else:
            apply_items_parallelly(self.items, workers)

    def run(self, command, sudo=True):
        chan = self._ssh_client.get_transport().open_session()
        chan.get_pty()
        if sudo:
            command = "sudo " + command
        chan.exec_command(command)
        fstdout = chan.makefile('rb', -1)
        fstderr = chan.makefile_stderr('rb', -1)
        result = RunResult()
        result.stdout = fstdout.read()
        result.stderr = fstderr.read()
        result.returncode = chan.recv_exit_status()
        return result
