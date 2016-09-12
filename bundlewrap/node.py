# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime, timedelta
from os import environ
from sys import exit
from threading import Lock

from . import operations
from .bundle import Bundle
from .concurrency import WorkerPool
from .deps import (
    DummyItem,
    find_item,
)
from .exceptions import (
    FaultUnavailable,
    ItemDependencyError,
    NodeLockedException,
    NoSuchBundle,
    RepositoryError,
)
from .group import GROUP_ATTR_DEFAULTS
from .itemqueue import ItemQueue, ItemTestQueue
from .items import Item
from .lock import NodeLock
from .metadata import check_for_unsolvable_metadata_key_conflicts, hash_metadata
from .utils import cached_property, graph_for_items, names
from .utils.statedict import hash_statedict
from .utils.text import blue, bold, cyan, green, red, validate_name, yellow
from .utils.text import force_text, mark_for_translation as _
from .utils.ui import io


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


def format_node_result(result):
    output = []
    output.append(("{count} OK").format(count=result.correct))

    if result.fixed:
        output.append(green(_("{count} fixed").format(count=result.fixed)))
    else:
        output.append(_("{count} fixed").format(count=result.fixed))

    if result.skipped:
        output.append(yellow(_("{count} skipped").format(count=result.skipped)))
    else:
        output.append(_("{count} skipped").format(count=result.skipped))

    if result.failed:
        output.append(red(_("{count} failed").format(count=result.failed)))
    else:
        output.append(_("{count} failed").format(count=result.failed))

    return ", ".join(output)


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


def apply_items(
    node,
    autoskip_selector="",
    my_soft_locks=(),
    other_peoples_soft_locks=(),
    workers=1,
    interactive=False,
    profiling=False,
):
    with io.job(_("  {node}  processing dependencies...").format(node=node.name)):
        item_queue = ItemQueue(node.items)

    results = []

    def tasks_available():
        return bool(item_queue.items_without_deps)

    def next_task():
        item, skipped_items = item_queue.pop()
        for skipped_item in skipped_items:
            handle_apply_result(
                node,
                skipped_item,
                Item.STATUS_SKIPPED,
                interactive,
                changes=[_("no pre-trigger")],
            )
            results.append((skipped_item.id, Item.STATUS_SKIPPED, timedelta(0)))

        return {
            'task_id': "{}:{}".format(node.name, item.id),
            'target': item.apply,
            'kwargs': {
                'autoskip_selector': autoskip_selector,
                'my_soft_locks': my_soft_locks,
                'other_peoples_soft_locks': other_peoples_soft_locks,
                'interactive': interactive,
            },
        }

    def handle_result(task_id, return_value, duration):
        item_id = task_id.split(":", 1)[1]
        item = find_item(item_id, item_queue.pending_items)

        status_code, changes = return_value

        if status_code == Item.STATUS_FAILED:
            for skipped_item in item_queue.item_failed(item):
                handle_apply_result(
                    node,
                    skipped_item,
                    Item.STATUS_SKIPPED,
                    interactive,
                    changes=[_("dep failed")],
                )
                results.append((skipped_item.id, Item.STATUS_SKIPPED, timedelta(0)))
        elif status_code in (Item.STATUS_FIXED, Item.STATUS_ACTION_SUCCEEDED):
            item_queue.item_fixed(item)
        elif status_code == Item.STATUS_OK:
            item_queue.item_ok(item)
        elif status_code == Item.STATUS_SKIPPED:
            for skipped_item in item_queue.item_skipped(item):
                skipped_reason = [_("dep skipped")]
                for lock in other_peoples_soft_locks:
                    for selector in lock['items']:
                        if skipped_item.covered_by_autoskip_selector(selector):
                            skipped_reason = [_("soft locked")]
                            break
                handle_apply_result(
                    node,
                    skipped_item,
                    Item.STATUS_SKIPPED,
                    interactive,
                    changes=skipped_reason,
                )
                results.append((skipped_item.id, Item.STATUS_SKIPPED, timedelta(0)))
        else:
            raise AssertionError(_(
                "unknown item status returned for {item}: {status}".format(
                    item=item.id,
                    status=repr(status_code),
                ),
            ))

        handle_apply_result(node, item, status_code, interactive, changes=changes)
        if not isinstance(item, DummyItem):
            results.append((item.id, status_code, duration))

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_result=handle_result,
        pool_id="apply_{}".format(node.name),
        workers=workers,
    )
    worker_pool.run()

    # we have no items without deps left and none are processing
    # there must be a loop
    if item_queue.items_with_deps:
        io.debug(_(
            "There was a dependency problem. Look at the debug.svg generated "
            "by the following command and try to find a loop:\n"
            "printf '{}' | dot -Tsvg -odebug.svg"
        ).format("\\n".join(graph_for_items(node.name, item_queue.items_with_deps))))

        raise ItemDependencyError(
            _("bad dependencies between these items: {}").format(
                ", ".join([i.id for i in item_queue.items_with_deps]),
            )
        )

    return results


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
    if changes is True:
        changes_text = "({})".format(_("create"))
    elif changes is False:
        changes_text = "({})".format(_("remove"))
    elif changes is None:
        changes_text = ""
    else:
        changes_text = "({})".format(", ".join(sorted(changes)))
    if result == Item.STATUS_FAILED:
        return "{x} {node}  {bundle}  {item} {status} {changes}".format(
            bundle=bold(bundle),
            changes=changes_text,
            item=item,
            node=bold(node),
            status=red(_("failed")),
            x=bold(red("✘")),
        )
    elif result == Item.STATUS_ACTION_SUCCEEDED:
        return "{x} {node}  {bundle}  {item} {status}".format(
            bundle=bold(bundle),
            item=item,
            node=bold(node),
            status=green(_("succeeded")),
            x=bold(green("✓")),
        )
    elif result == Item.STATUS_SKIPPED:
        return "{x} {node}  {bundle}  {item} {status} {changes}".format(
            bundle=bold(bundle),
            changes=changes_text,
            item=item,
            node=bold(node),
            x=bold(yellow("»")),
            status=yellow(_("skipped")),
        )
    elif result == Item.STATUS_FIXED:
        return "{x} {node}  {bundle}  {item} {status} {changes}".format(
            bundle=bold(bundle),
            changes=changes_text,
            item=item,
            node=bold(node),
            x=bold(green("✓")),
            status=green(_("fixed")),
        )


class Node(object):
    OS_FAMILY_BSD = (
        'freebsd',
        'macos',
        'netbsd',
        'openbsd',
    )
    OS_FAMILY_DEBIAN = (
        'debian',
        'ubuntu',
        'raspbian',
    )
    OS_FAMILY_REDHAT = (
        'rhel',
        'centos',
        'fedora',
    )

    OS_FAMILY_LINUX = (
        'amazonlinux',
        'arch',
        'opensuse',
        'gentoo',
        'linux',
        'oraclelinux',
    ) + \
        OS_FAMILY_DEBIAN + \
        OS_FAMILY_REDHAT

    OS_KNOWN = OS_FAMILY_BSD + OS_FAMILY_LINUX

    def __init__(self, name, infodict=None):
        if infodict is None:
            infodict = {}

        if not validate_name(name):
            raise RepositoryError(_("'{}' is not a valid node name").format(name))

        self.name = name
        self._bundles = infodict.get('bundles', [])
        self._compiling_metadata = Lock()
        self._metadata_so_far = {}
        self._node_metadata = infodict.get('metadata', {})
        self._ssh_conn_established = False
        self._ssh_first_conn_lock = Lock()
        self.add_ssh_host_keys = False
        self.hostname = infodict.get('hostname', self.name)

        for attr in GROUP_ATTR_DEFAULTS:
            setattr(self, "_{}".format(attr), infodict.get(attr))

    def __lt__(self, other):
        return self.name < other.name

    def __repr__(self):
        return "<Node '{}'>".format(self.name)

    @cached_property
    def bundles(self):
        with io.job(_("  {node}  loading bundles...").format(node=self.name)):
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
    def cdict(self):
        node_dict = {}
        for item in self.items:
            try:
                node_dict[item.id] = item.hash()
            except AttributeError:  # actions have no cdict
                pass
        return node_dict

    def covered_by_autoskip_selector(self, autoskip_selector):
        """
        True if this node should be skipped based on the given selector
        string (e.g. "node:foo,group:bar").
        """
        components = [c.strip() for c in autoskip_selector.split(",")]
        if "node:{}".format(self.name) in components:
            return True
        for group in self.groups:
            if "group:{}".format(group.name) in components:
                return True
        return False

    def group_membership_hash(self):
        return hash_statedict(sorted(names(self.groups)))

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
        return hash_statedict(self.cdict)

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

    @cached_property
    def items(self):
        if not self.dummy:
            for bundle in self.bundles:
                for item in bundle.items:
                    yield item

    @property
    def _static_items(self):
        for bundle in self.bundles:
            for item in bundle._static_items:
                yield item

    def apply(
        self,
        autoskip_selector="",
        interactive=False,
        force=False,
        workers=4,
        profiling=False,
    ):
        if not list(self.items):
            io.stdout(_("{x} {node}  has no items").format(node=bold(self.name), x=yellow("!")))
            return None

        if self.covered_by_autoskip_selector(autoskip_selector):
            io.debug(_("skipping {}, matches autoskip selector").format(self.name))
            return None

        start = datetime.now()

        io.stdout(_("{x} {node} run started at {time}").format(
            node=bold(self.name),
            time=start.strftime("%Y-%m-%d %H:%M:%S"),
            x=blue("i"),
        ))
        self.repo.hooks.node_apply_start(
            self.repo,
            self,
            interactive=interactive,
        )

        try:
            with NodeLock(self, interactive=interactive, ignore=force) as lock:
                item_results = apply_items(
                    self,
                    autoskip_selector=autoskip_selector,
                    my_soft_locks=lock.my_soft_locks,
                    other_peoples_soft_locks=lock.other_peoples_soft_locks,
                    workers=workers,
                    interactive=interactive,
                    profiling=profiling,
                )
        except NodeLockedException as e:
            if not interactive:
                io.stderr(_("{x} {node} already locked by {user} at {date} ({duration} ago, `bw apply -f` to override)").format(
                    date=bold(e.args[0]['date']),
                    duration=e.args[0]['duration'],
                    node=bold(self.name),
                    user=bold(e.args[0]['user']),
                    x=red("!"),
                ))
            item_results = []
        result = ApplyResult(self, item_results)
        result.start = start
        result.end = datetime.now()

        io.stdout(_("{x} {node} run completed after {time}s").format(
            node=bold(self.name),
            time=(result.end - start).total_seconds(),
            x=blue("i"),
        ))
        io.stdout(_("{x} {node} stats: {stats}").format(
            node=bold(self.name),
            stats=format_node_result(result),
            x=blue("i"),
        ))

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
            add_host_keys=True if environ.get('BW_ADD_HOST_KEYS', False) == "1" else False,
            wrapper_inner=self.cmd_wrapper_inner,
            wrapper_outer=self.cmd_wrapper_outer,
        )

    def get_item(self, item_id):
        return find_item(item_id, self.items)

    @property
    def metadata(self):
        """
        Returns full metadata for a node. MUST NOT be used from inside a
        metadata processor. Use .partial_metadata instead.
        """
        return self.repo._metadata_for_node(self.name, partial=False)

    def metadata_hash(self):
        return hash_metadata(self.metadata)

    @property
    def metadata_processors(self):
        for bundle in self.bundles:
            for metadata_processor in bundle.metadata_processors:
                yield metadata_processor

    @property
    def partial_metadata(self):
        """
        Only to be used from inside metadata processors. Can't use the
        normal .metadata there because it might deadlock when nodes
        have interdependent metadata.

        It's OK for metadata processors to work with partial metadata
        because they will be fed all metadata updates until no more
        changes are made by any metadata processor.
        """
        return self.repo._metadata_for_node(self.name, partial=True)

    def run(self, command, may_fail=False, log_output=False):
        if log_output:
            def log_function(msg):
                io.stdout("{x} {node}  {msg}".format(
                    node=bold(self.name),
                    msg=force_text(msg).rstrip("\n"),
                    x=cyan("›"),
                ))
        else:
            log_function = None

        add_host_keys = True if environ.get('BW_ADD_HOST_KEYS', False) == "1" else False

        if not self._ssh_conn_established:
            # Sometimes we're opening SSH connections to a node too fast
            # for OpenSSH to establish the ControlMaster socket for the
            # second and following connections to use.
            # To prevent this, we just wait until a first dummy command
            # has completed on the node before trying to reuse the
            # multiplexed connection.
            if self._ssh_first_conn_lock.acquire(False):
                try:
                    operations.run(self.hostname, "true", add_host_keys=add_host_keys)
                    self._ssh_conn_established = True
                finally:
                    self._ssh_first_conn_lock.release()
            else:
                # we didn't get the lock immediately, now we just wait
                # until it is released before we proceed
                with self._ssh_first_conn_lock:
                    pass

        return operations.run(
            self.hostname,
            command,
            add_host_keys=add_host_keys,
            ignore_failure=may_fail,
            log_function=log_function,
            wrapper_inner=self.cmd_wrapper_inner,
            wrapper_outer=self.cmd_wrapper_outer,
        )

    def test(self, ignore_missing_faults=False, workers=4):
        with io.job(_("  {node}  checking for metadata collisions...").format(node=self.name)):
            check_for_unsolvable_metadata_key_conflicts(self)
        io.stdout(_("{x} {node}  has no metadata collisions").format(
            x=green("✓"),
            node=bold(self.name),
        ))
        if self.items:
            test_items(self, ignore_missing_faults=ignore_missing_faults, workers=workers)
        else:
            io.stdout(_("{x} {node}  has no items").format(node=bold(self.name), x=yellow("!")))

        self.repo.hooks.test_node(self.repo, self)

    def upload(self, local_path, remote_path, mode=None, owner="", group=""):
        return operations.upload(
            self.hostname,
            local_path,
            remote_path,
            add_host_keys=True if environ.get('BW_ADD_HOST_KEYS', False) == "1" else False,
            group=group,
            mode=mode,
            owner=owner,
            wrapper_inner=self.cmd_wrapper_inner,
            wrapper_outer=self.cmd_wrapper_outer,
        )

    def verify(self, show_all=False, workers=4):
        bad = 0
        good = 0
        if not self.items:
            io.stdout(_("{x} {node}  has no items").format(node=bold(self.name), x=yellow("!")))
        else:
            for item_status in verify_items(
                self,
                show_all=show_all,
                workers=workers,
            ):
                if item_status:
                    good += 1
                else:
                    bad += 1

        return {'good': good, 'bad': bad}


def build_attr_property(attr, default):
    def method(self):
        attr_source = None
        attr_value = None
        group_order = [
            self.repo.get_group(group_name)
            for group_name in _flatten_group_hierarchy(self.groups)
        ]

        for group in group_order:
            if getattr(group, attr) is not None:
                attr_source = "group:{}".format(group.name)
                attr_value = getattr(group, attr)

        if getattr(self, "_{}".format(attr)) is not None:
            attr_source = "node"
            attr_value = getattr(self, "_{}".format(attr))

        if attr_value is None:
            attr_source = "default"
            attr_value = default

        io.debug(_("node {node} gets its {attr} attribute from: {source}").format(
            node=self.name,
            attr=attr,
            source=attr_source,
        ))
        return attr_value
    method.__name__ = str("_group_attr_{}".format(attr))  # required for cached_property
                                                          # str() for Python 2 compatibility
    return cached_property(method)

for attr, default in GROUP_ATTR_DEFAULTS.items():
    setattr(Node, attr, build_attr_property(attr, default))


def test_items(node, ignore_missing_faults=False, workers=1):
    item_queue = ItemTestQueue(node.items)

    def tasks_available():
        return bool(item_queue.items_without_deps)

    def next_task():
        try:
            # Get the next non-DummyItem in the queue.
            while True:
                item = item_queue.pop()
                if not isinstance(item, DummyItem):
                    break
        except IndexError:  # no more items available right now
            return None
        else:
            return {
                'task_id': item.node.name + ":" + item.bundle.name + ":" + item.id,
                'target': item.test,
            }

    def handle_result(task_id, return_value, duration):
        node_name, bundle_name, item_id = task_id.split(":", 2)
        io.stdout("{x} {node}  {bundle}  {item}".format(
            bundle=bold(bundle_name),
            item=item_id,
            node=bold(node_name),
            x=green("✓"),
        ))

    def handle_exception(task_id, exception, traceback):
        node_name, bundle_name, item_id = task_id.split(":", 2)
        if ignore_missing_faults and isinstance(exception, FaultUnavailable):
            io.stderr(_("{x} {node}  {bundle}  {item}  (Fault missing)").format(
                bundle=bold(bundle_name),
                item=item_id,
                node=bold(node_name),
                x=yellow("!"),
            ))
        else:
            io.stderr("{x} {node}  {bundle}  {item}".format(
                bundle=bold(bundle_name),
                item=item_id,
                node=bold(node_name),
                x=red("!"),
            ))
            io.stderr(traceback)
            io.stderr("{}: {}".format(type(exception), str(exception)))
            exit(1)

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_result=handle_result,
        handle_exception=handle_exception,
        pool_id="test_{}".format(node.name),
        workers=workers,
    )
    worker_pool.run()

    if item_queue.items_with_deps:
        io.stderr(_(
            "There was a dependency problem. Look at the debug.svg generated "
            "by the following command and try to find a loop:\n"
            "printf '{}' | dot -Tsvg -odebug.svg"
        ).format("\\n".join(graph_for_items(node.name, item_queue.items_with_deps))))

        raise ItemDependencyError(
            _("bad dependencies between these items: {}").format(
                ", ".join([i.id for i in item_queue.items_with_deps]),
            )
        )


def verify_items(node, show_all=False, workers=1):
    items = []
    for item in node.items:
        if (
            not item.ITEM_TYPE_NAME == 'action' and
            not item.triggered
        ):
            items.append(item)

    def tasks_available():
        return bool(items)

    def next_task():
        while True:
            try:
                item = items.pop()
            except IndexError:
                return None
            if item._faults_missing_for_attributes:
                if item.error_on_missing_fault:
                    item._raise_for_faults()
                else:
                    io.stdout(_("{x} {node}  {bundle}  {item}  (unavailable)").format(
                        bundle=bold(item.bundle.name),
                        item=item.id,
                        node=bold(node.name),
                        x=yellow("»"),
                    ))
            else:
                return {
                    'task_id': node.name + ":" + item.bundle.name + ":" + item.id,
                    'target': item.get_status,
                }

    def handle_result(task_id, item_status, duration):
        node_name, bundle_name, item_id = task_id.split(":", 2)
        if not item_status.correct:
            if item_status.must_be_created:
                changes_text = _("create")
            elif item_status.must_be_deleted:
                changes_text = _("remove")
            else:
                changes_text = ", ".join(sorted(item_status.keys_to_fix))
            io.stderr("{x} {node}  {bundle}  {item} ({changes})".format(
                bundle=bold(bundle_name),
                changes=changes_text,
                item=item_id,
                node=bold(node_name),
                x=red("✘"),
            ))
            return False
        else:
            if show_all:
                io.stdout("{x} {node}  {bundle}  {item}".format(
                    bundle=bold(bundle_name),
                    item=item_id,
                    node=bold(node_name),
                    x=green("✓"),
                ))
            return True

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_result,
        pool_id="verify_{}".format(node.name),
        workers=workers,
    )
    return worker_pool.run()
