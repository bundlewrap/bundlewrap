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
    DummyItem,
    find_item,
    prepare_dependencies,
)
from .exceptions import (
    BundleError,
    ItemDependencyError,
    NodeAlreadyLockedException,
    NoSuchBundle,
    RepositoryError,
)
from .itemqueue import ItemQueue
from .items import Item
from .utils import cached_property, graph_for_items, merge_dict, names
from .utils.statedict import hash_statedict
from .utils.text import blue, bold, cyan, green, red, validate_name, wrap_question, yellow
from .utils.text import force_text, mark_for_translation as _
from .utils.ui import io

LOCK_PATH = "/tmp/bundlewrap.lock"
LOCK_FILE = LOCK_PATH + "/info"
META_PROC_MAX_ITER = 9999  # maximum iterations for metadata processors


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


def apply_items(node, autoskip_selector="", workers=1, interactive=False, profiling=False):
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
                        handle_apply_result(
                            node,
                            skipped_item,
                            Item.STATUS_SKIPPED,
                            interactive,
                            changes=[_("no pre-trigger")],
                        )
                        yield(skipped_item.id, Item.STATUS_SKIPPED, timedelta(0))

                    # start_task() increases jobs_open.
                    worker_pool.start_task(
                        msg['wid'],
                        item.apply,
                        task_id=item.id,
                        kwargs={
                            'autoskip_selector': autoskip_selector,
                            'interactive': interactive,
                        },
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
                        handle_apply_result(
                            node,
                            skipped_item,
                            Item.STATUS_SKIPPED,
                            interactive,
                            changes=[_("dep failed")],
                        )
                        yield(skipped_item.id, Item.STATUS_SKIPPED, timedelta(0))
                elif status_code in (Item.STATUS_FIXED, Item.STATUS_ACTION_SUCCEEDED):
                    item_queue.item_fixed(item)
                elif status_code == Item.STATUS_OK:
                    item_queue.item_ok(item)
                elif status_code == Item.STATUS_SKIPPED:
                    for skipped_item in item_queue.item_skipped(item):
                        handle_apply_result(
                            node,
                            skipped_item,
                            Item.STATUS_SKIPPED,
                            interactive,
                            changes=[_("dep skipped")],
                        )
                        yield(skipped_item.id, Item.STATUS_SKIPPED, timedelta(0))
                else:
                    raise AssertionError(_(
                        "unknown item status returned for {item}: {status}".format(
                            item=item.id,
                            status=repr(status_code),
                        ),
                    ))

                handle_apply_result(node, item, status_code, interactive, changes=changes)
                if not isinstance(item, DummyItem):
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
    OS_LINUX = 'linux'
    OS_MACOSX = 'macosx'
    OS_OPENBSD = 'openbsd'

    OS_ALIASES = {
        'linux': OS_LINUX,
        'macosx': OS_MACOSX,
        'openbsd': OS_OPENBSD,
    }

    def __init__(self, name, infodict=None):
        if infodict is None:
            infodict = {}

        if not validate_name(name):
            raise RepositoryError(_("'{}' is not a valid node name").format(name))

        self.name = name
        self._bundles = infodict.get('bundles', [])
        self._compiling_metadata = False
        self._node_metadata = infodict.get('metadata', {})
        self._node_os = infodict.get('os')
        self.add_ssh_host_keys = False
        self.hostname = infodict.get('hostname', self.name)
        self.use_shadow_passwords = infodict.get('use_shadow_passwords', True)

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

    def apply(
        self,
        autoskip_selector="",
        interactive=False,
        force=False,
        workers=4,
        profiling=False,
    ):
        if not list(self.items):
            io.debug(_("not applying to {}, it has no items").format(self.name))
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
            with NodeLock(self, interactive, ignore=force):
                item_results = list(apply_items(
                    self,
                    autoskip_selector=autoskip_selector,
                    workers=workers,
                    interactive=interactive,
                    profiling=profiling,
                ))
        except NodeAlreadyLockedException as e:
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
            add_host_keys=True if environ.get('BWADDHOSTKEYS', False) == "1" else False,
        )

    def get_item(self, item_id):
        return find_item(item_id, self.items)

    @cached_property
    def metadata(self):
        if self._compiling_metadata:
            raise BundleError("trying to access metadata while it is "
                              "being compiled (check your metadata.py)")
        else:
            self._compiling_metadata = True
        m = {}

        with io.job(_("  {node}  building group metadata...").format(node=self.name)):
            group_order = _flatten_group_hierarchy(self.groups)
            for group_name in group_order:
                m = merge_dict(m, self.repo.get_group(group_name).metadata)

        with io.job(_("  {node}  merging node metadata...").format(node=self.name)):
            m = merge_dict(m, self._node_metadata)

        with io.job(_("  {node}  running metadata processors...").format(node=self.name)):
            iterations = {}
            while not iterations or max(iterations.values()) <= META_PROC_MAX_ITER:
                modified = False
                for metadata_processor in self.metadata_processors:
                    iterations.setdefault(metadata_processor.__name__, 1)
                    processed = metadata_processor(m.copy())
                    assert isinstance(processed, dict)
                    if processed != m:
                        m = processed
                        iterations[metadata_processor.__name__] += 1
                        modified = True
                if not modified:
                    break

        for metadata_processor, number_of_iterations in iterations.items():
            if number_of_iterations >= META_PROC_MAX_ITER:
                raise BundleError(_(
                    "metadata processor '{proc}' stopped after too many iterations "
                    "({max_iter}) for node '{node}' to prevent infinite loop".format(
                        max_iter=META_PROC_MAX_ITER,
                        node=self.name,
                        proc=metadata_processor,
                    ),
                ))

        self._compiling_metadata = False
        return m

    @property
    def metadata_processors(self):
        for bundle in self.bundles:
            for metadata_processor in bundle.metadata_processors:
                yield metadata_processor

    @cached_property
    def os(self):
        os = None

        group_order = _flatten_group_hierarchy(self.groups)
        for group_name in group_order:
            group = self.repo.get_group(group_name)
            os = os if group.os is None else group.os

        os = self._node_os if os is None else os
        os = 'linux' if os is None else os

        return self.OS_ALIASES[os.lower()]

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
        self.repo.hooks.test_node(self.repo, self)

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
            with io.job(_("  {node}  getting lock status...").format(node=self.node.name)):
                result = self.node.run("mkdir " + quote(LOCK_PATH), may_fail=True)
                if result.return_code != 0:
                    self.node.download(LOCK_FILE, local_path, ignore_failure=True)
                    with open(local_path, 'r') as f:
                        try:
                            info = json.loads(f.read())
                        except:
                            io.stderr(_(
                                "{warning}  corrupted lock on {node}: "
                                "unable to read or parse lock file contents "
                                "(clear it with `rm -R {path}`)"
                            ).format(
                                node=self.node.name,
                                path=LOCK_FILE,
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
                        info['duration'] = str(datetime.now() - datetime.fromtimestamp(d)).split(".")[0]
                    if 'user' not in info:
                        info['user'] = _("<unknown>")
                    if self.ignore or (self.interactive and io.ask(
                        self._warning_message(info),
                        False,
                        epilogue=blue("?") + " " + bold(self.node.name),
                    )):
                        pass
                    else:
                        raise NodeAlreadyLockedException(info)

            with io.job(_("  {node}  uploading lock file...").format(node=self.node.name)):
                with open(local_path, 'w') as f:
                    f.write(json.dumps({
                        'date': time(),
                        'user': environ.get('BW_IDENTITY', "{}@{}".format(
                            getuser(),
                            gethostname(),
                        )),
                    }))
                self.node.upload(local_path, LOCK_FILE)
        finally:
            remove(local_path)

    def __exit__(self, type, value, traceback):
        with io.job(_("  {node}  removing lock...").format(node=self.node.name)):
            result = self.node.run("rm -R {}".format(quote(LOCK_PATH)), may_fail=True)

        if result.return_code != 0:
            io.stderr(_("Could not release lock for node '{node}'").format(
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


def test_items(items, workers=1):
    items = prepare_dependencies(items)

    with WorkerPool(workers=workers) as worker_pool:
        while worker_pool.keep_running():
            msg = worker_pool.get_event()
            if msg['msg'] == 'REQUEST_WORK':
                while True:
                    if items:
                        item = items.pop()
                        if isinstance(item, DummyItem):
                            continue
                        worker_pool.start_task(
                            msg['wid'],
                            item.test,
                            task_id=item.node.name + ":" + item.bundle.name + ":" + item.id,
                        )
                        break
                    else:
                        worker_pool.quit(msg['wid'])
                        break
            elif msg['msg'] == 'FINISHED_WORK':
                node_name, bundle_name, item_id = msg['task_id'].split(":", 2)
                io.stdout("{x} {node}  {bundle}  {item}".format(
                    bundle=bold(bundle_name),
                    item=item_id,
                    node=bold(node_name),
                    x=green("✓"),
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
                        task_id=item.node.name + ":" + item.bundle.name + ":" + item.id,
                    )
                else:
                    worker_pool.quit(msg['wid'])
            elif msg['msg'] == 'FINISHED_WORK':
                node_name, bundle_name, item_id = msg['task_id'].split(":", 2)
                item_status = msg['return_value']
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
                    yield False
                else:
                    if show_all:
                        io.stdout("{x} {node}  {bundle}  {item}".format(
                            bundle=bold(bundle_name),
                            item=item_id,
                            node=bold(node_name),
                            x=green("✓"),
                        ))
                    yield True
