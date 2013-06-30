from copy import copy

from paramiko.client import SSHClient, WarningPolicy

from .bundle import Bundle
from .exceptions import ItemDependencyError, RepositoryError
from .utils import cached_property, mark_for_translation as _, validate_name


def order_items(unordered_items):
    """
    Takes a list of items and returns them in an order that honors
    dependencies.

    Raises ItemDependencyError if there is a problem (e.g. dependency
    loop).
    """
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

    # first, find all types of items and add dummy deps
    dummy_items = {}
    for item in unordered_items:
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
    all_items = list(dummy_items.values()) + unordered_items

    # find items without deps to start with
    nodeps = []
    withdeps = []
    while all_items:
        item = all_items.pop()
        if item._deps:
            withdeps.append(item)
        else:
            nodeps.append(item)

    ordered_items = []

    while nodeps:
        item = nodeps.pop()
        if not isinstance(item, DummyItem):
            # item without pending deps can be added to exec order
            # this is only done for non-dummy items
            # dummy items are not needed beyond this point
            ordered_items.append(item)

        # loop over pending items and remove satisfied dep
        for pending_item in copy(withdeps):
            try:
                pending_item._deps.remove(item.id)
            except ValueError:
                pass
            if not pending_item._deps:
                nodeps.append(pending_item)
                withdeps.remove(pending_item)
    if withdeps:
        raise ItemDependencyError(
            "Bad dependencies between these items: {}".format(
                ", ".join([repr(i) for i in withdeps]),
            ),
        )

    return ordered_items


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
