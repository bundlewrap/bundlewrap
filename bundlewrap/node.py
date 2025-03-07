from contextlib import suppress
from datetime import datetime, timedelta
from hashlib import md5
from os import environ, mkdir, rename
from os.path import dirname, exists, join
from threading import Lock

from tomlkit import dumps as toml_dump, parse as toml_parse

from . import operations
from .bundle import Bundle
from .concurrency import WorkerPool
from .deps import find_item, ItemDependencyLoop
from .exceptions import (
    BundleError,
    GracefulApplyException,
    ItemSkipped,
    NodeLockedException,
    NoSuchBundle,
    NoSuchGroup,
    RemoteException,
    TransportException,
    RepositoryError,
    SkipNode,
)
from .group import GROUP_ATTR_DEFAULTS, GROUP_ATTR_TYPES, GROUP_ATTR_TYPES_ENFORCED
from .itemqueue import ItemQueue
from .items import Item
from .lock import NodeLock
from .metadata import hash_metadata
from .utils import (
    cached_property,
    cached_property_set,
    error_context,
    get_file_contents,
    names,
)
from .utils.dicts import (
    dict_to_text,
    dict_to_toml,
    diff_dict,
    hash_statedict,
    set_key_at_path,
    normalize_dict,
    validate_dict,
    COLLECTION_OF_STRINGS,
)
from .utils.text import (
    blue,
    bold,
    cyan,
    force_text,
    format_duration,
    green,
    mark_for_translation as _,
    prefix_lines,
    red,
    toml_clean,
    validate_name,
    yellow,
)
from .utils.ui import io


NODE_ATTR_TYPES = GROUP_ATTR_TYPES.copy()
NODE_ATTR_TYPES['groups'] = COLLECTION_OF_STRINGS
NODE_ATTR_TYPES['hostname'] = str
NODE_ATTRS = sorted(list(GROUP_ATTR_DEFAULTS) + ['bundles', 'file_path', 'groups', 'hostname'])


class ApplyResult:
    """
    Holds information about an apply run for a node.
    """
    def __init__(self, node, item_results):
        self.node_name = node.name
        self.correct = 0
        self.fixed = 0
        self.skipped = 0
        self.failed = 0
        self.total = 0

        for item_id, result, duration in item_results:
            self.total += 1
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

        self.start = None
        self.end = None

    def __lt__(self, other):
        return self.node_name < other.node_name

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


def handle_apply_result(
    node,
    item,
    status_code,
    interactive=False,
    details=None,
    show_diff=True,
    created=None,
    deleted=None,
    show_skipped_items=True,
):
    if status_code == Item.STATUS_SKIPPED and details in (
        Item.SKIP_REASON_NO_TRIGGER,
        Item.SKIP_REASON_UNLESS,
    ):
        # skipped for "unless" or "not triggered", don't output those
        return

    if status_code == Item.STATUS_SKIPPED and not show_skipped_items:
        return

    formatted_result = format_item_result(
        status_code,
        node.name,
        item.bundle.name,
        item.id,
        interactive=interactive,
        details=details,
        show_diff=show_diff,
        created=created,
        deleted=deleted,
    )
    if formatted_result is not None:
        if status_code == Item.STATUS_FAILED:
            io.stderr(formatted_result)
            if item._command_results:
                io.stderr(format_item_command_results(item._command_results))
                # free up memory
                del item._command_results
        else:
            io.stdout(formatted_result)


def apply_items(
    node,
    autoskip_selector="",
    autoonly_selector="",
    my_soft_locks=(),
    other_peoples_soft_locks=(),
    workers=1,
    interactive=False,
    show_diff=True,
    show_skipped_items=True,
):
    item_queue = ItemQueue(node)
    # the item queue might contain new generated items (canned actions)
    # adjust progress total accordingly
    extra_items = len(item_queue.all_items) - len(node.items)
    io.progress_increase_total(increment=extra_items)

    results = []

    def tasks_available():
        # Some item types are not allowed to run at the same time as
        # some other item types. items_without_deps_runnable handles
        # these cases.
        return bool(item_queue.items_without_deps_runnable())

    def next_task():
        item = item_queue.pop()
        return {
            'task_id': "{}:{}".format(node.name, item.id),
            'target': item.apply,
            'kwargs': {
                'autoskip_selector': autoskip_selector,
                'autoonly_selector': autoonly_selector,
                'my_soft_locks': my_soft_locks,
                'other_peoples_soft_locks': other_peoples_soft_locks,
                'interactive': interactive,
                'show_diff': show_diff,
            },
        }

    def handle_result(task_id, return_value, duration):
        item_id = task_id.split(":", 1)[1]
        item = find_item(item_id, item_queue.pending_items)

        status_code, details, created, deleted = return_value

        if status_code == Item.STATUS_FAILED:
            for skipped_item in item_queue.item_failed(item):
                handle_apply_result(
                    node,
                    skipped_item,
                    Item.STATUS_SKIPPED,
                    interactive=interactive,
                    details=Item.SKIP_REASON_DEP_FAILED,
                    show_skipped_items=show_skipped_items,
                )
                results.append((skipped_item.id, Item.STATUS_SKIPPED, timedelta(0)))
        elif status_code in (Item.STATUS_FIXED, Item.STATUS_ACTION_SUCCEEDED):
            item_queue.item_fixed(item)
        elif status_code == Item.STATUS_OK:
            item_queue.item_ok(item)
        elif status_code == Item.STATUS_SKIPPED:
            for skipped_item in item_queue.item_skipped(item):
                skip_reason = Item.SKIP_REASON_DEP_SKIPPED
                for lock in other_peoples_soft_locks:
                    for selector in lock['items']:
                        if skipped_item.covered_by_autoskip_selector(selector):
                            skip_reason = Item.SKIP_REASON_SOFTLOCK
                            break
                handle_apply_result(
                    node,
                    skipped_item,
                    Item.STATUS_SKIPPED,
                    interactive=interactive,
                    details=skip_reason,
                    show_skipped_items=show_skipped_items,
                )
                results.append((skipped_item.id, Item.STATUS_SKIPPED, timedelta(0)))
        else:
            raise AssertionError(_(
                "unknown item status returned for {item}: {status}".format(
                    item=item.id,
                    status=repr(status_code),
                ),
            ))

        handle_apply_result(
            node,
            item,
            status_code,
            interactive=interactive,
            details=details,
            show_diff=show_diff,
            created=created,
            deleted=deleted,
            show_skipped_items=show_skipped_items,
        )
        io.progress_advance()
        results.append((item.id, status_code, duration))

    def handle_exception(task_id, exc, traceback):
        item_id = task_id.split(":", 1)[1]
        item = find_item(item_id, item_queue.pending_items)

        for skipped_item in item_queue.item_failed(item):
            handle_apply_result(
                node,
                skipped_item,
                Item.STATUS_SKIPPED,
                interactive=interactive,
                details=Item.SKIP_REASON_DEP_FAILED,
                show_skipped_items=show_skipped_items,
            )
            results.append((skipped_item.id, Item.STATUS_SKIPPED, timedelta(0)))

        handle_apply_result(
            node,
            item,
            Item.STATUS_FAILED,
            interactive=interactive,
            details=None,
            show_diff=False,
            show_skipped_items=show_skipped_items,
        )
        results.append((item.id, Item.STATUS_FAILED, timedelta(0)))
        output = prefix_lines(traceback, red("│ "))
        output += prefix_lines(repr(exc), red("│ "))
        output += red("╵")
        io.stderr(output)
        io.progress_advance()

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_result=handle_result,
        handle_exception=handle_exception,
        pool_id="apply_{}".format(node.name),
        workers=workers,
    )
    worker_pool.run()

    # we have no items without deps left and none are processing
    # there must be a loop
    if item_queue.items_with_deps:
        raise ItemDependencyLoop(item_queue.items_with_deps)

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
    for child_group in child_groups:
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
        for group in parent_groups:
            if top_level_group in parent_groups[group]:
                parent_groups[group].remove(top_level_group)

    return order


def format_item_command_results(results):
    output = ""

    for result in results:
        stdout = result['result'].stdout_text.strip()
        stderr = result['result'].stderr_text.strip()

        # show command
        output += "{b}".format(b=red('│'))
        output += "\n{b} {command} (return code: {code}{no_output})\n".format(
            b=red('├─'),
            command=bold(result['command']),
            code=bold(result['result'].return_code),
            no_output='' if stdout or stderr else '; no output'
        )

        # show output
        lines = ""
        if stdout or stderr:
            lines += "\n"
            if stdout:
                lines += stdout.strip()
            if stderr:
                lines += stderr.strip()

        output += prefix_lines(lines, red("│ "))

    output += red("╵")
    return output.lstrip('\n')


def format_item_result(
    result,
    node,
    bundle,
    item,
    interactive=False,
    details=None,
    show_diff=True,
    created=None,
    deleted=None,
):
    if created or deleted or details is None:
        details_text = ""
    elif result == Item.STATUS_SKIPPED:
        details_text = "({})".format(Item.SKIP_REASON_DESC[details])
    else:
        details_text = "({})".format(", ".join(sorted(details[2])))
    if result == Item.STATUS_FAILED:
        if created:
            status = red(_("failed to create"))
        elif deleted:
            status = red(_("failed to delete"))
        else:
            status = red(_("failed"))
        if show_diff and not created and not deleted:
            output = "{x} {node}  {bundle}  {item}  {status}\n".format(
                bundle=bold(bundle),
                item=item,
                node=bold(node),
                status=status,
                x=bold(red("✘")),
            )
            diff = diff_dict(details[1], details[0], skip_missing_in_target=True)
            output += prefix_lines(diff, f"{red('│')} ")
            output += red("╵")
            return output
        else:
            return "{x} {node}  {bundle}  {item}  {status} {details}".format(
                bundle=bold(bundle),
                details=details_text,
                item=item,
                node=bold(node),
                status=status,
                x=bold(red("✘")),
            )
    elif result == Item.STATUS_ACTION_SUCCEEDED:
        return "{x} {node}  {bundle}  {item}  {status}".format(
            bundle=bold(bundle),
            item=item,
            node=bold(node),
            status=green(_("succeeded")),
            x=bold(green("✓")),
        )
    elif result == Item.STATUS_SKIPPED:
        return "{x} {node}  {bundle}  {item}  {status} {details}".format(
            bundle=bold(bundle),
            details=details_text,
            item=item,
            node=bold(node),
            x=bold(yellow("»")),
            status=yellow(_("skipped")),
        )
    elif result == Item.STATUS_FIXED:
        if created:
            status = green(_("created"))
        elif deleted:
            status = green(_("deleted"))
        else:
            status = green(_("fixed"))
        if not interactive and show_diff:
            output = "{x} {node}  {bundle}  {item}  {status}\n".format(
                bundle=bold(bundle),
                item=item,
                node=bold(node),
                x=bold(green("✓")),
                status=status,
            )
            diff = "\n"
            if created:
                diff += dict_to_text(details, value_color=green)
            elif deleted:
                diff += dict_to_text(details, value_color=red)
            else:
                diff += diff_dict(details[1], details[0], skip_missing_in_target=True)
            output += prefix_lines(diff, f"{green('│')} ")
            output += green("╵")
            return output
        else:
            return "{x} {node}  {bundle}  {item}  {status}".format(
                bundle=bold(bundle),
                item=item,
                node=bold(node),
                x=bold(green("✓")),
                status=status,
            )


class Node:
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
        'oraclelinux',
    )

    OS_FAMILY_LINUX = (
        'alpine',
        'amazonlinux',
        'arch',
        'opensuse',
        'openwrt',
        'gentoo',
        'linux',
    ) + \
        OS_FAMILY_DEBIAN + \
        OS_FAMILY_REDHAT

    OS_FAMILY_UNIX = OS_FAMILY_BSD + OS_FAMILY_LINUX
    OS_KNOWN = OS_FAMILY_UNIX + ('kubernetes', 'routeros')

    def __init__(self, name, attributes=None):
        if attributes is None:
            attributes = {}

        if not validate_name(name):
            raise RepositoryError(_("'{}' is not a valid node name").format(name))

        with error_context(node_name=name):
            validate_dict(attributes, NODE_ATTR_TYPES)

        attributes = normalize_dict(attributes, GROUP_ATTR_TYPES_ENFORCED)

        self._add_host_keys = environ.get('BW_ADD_HOST_KEYS', False) == "1"
        self._attributes = attributes
        self._dynamic_attribute_cache = {}
        self._ssh_conn_established = False
        self._ssh_first_conn_lock = Lock()
        self.file_path = attributes.get('file_path')
        self.hostname = attributes.get('hostname', name)
        self.name = name

        for attr in GROUP_ATTR_DEFAULTS:
            setattr(self, "_{}".format(attr), attributes.get(attr))

    def __getattr__(self, name):
        with suppress(KeyError):
            return self._dynamic_attribute_cache[name]
        try:
            func = self.repo.node_attribute_functions[name]
        except KeyError:
            raise AttributeError(name)
        else:
            with error_context(node=self.name, attr=name):
                value = func(self)
            self._dynamic_attribute_cache[name] = value
            return value

    def __lt__(self, other):
        return self.name < other.name

    def __repr__(self):
        return "<Node '{}'>".format(self.name)

    def __str__(self):
        return self.name

    @cached_property_set
    def bundles(self):
        with io.job(_("{node}  loading bundles").format(node=bold(self.name))):
            bundle_names = set(self._attributes.get('bundles', set()))

            for group in self.groups:
                for bundle_name in set(group._attributes.get('bundles', set())):
                    bundle_names.add(bundle_name)

            for bundle_name in bundle_names:
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
            if item.ITEM_TYPE_NAME != 'action':  # actions have no cdict
                node_dict[item.id] = item.hash()
        return node_dict

    def covered_by_autoskip_selector(self, autoskip_selector):
        """
        True if this node should be skipped based on the given selector
        string (e.g. "node:foo,group:bar").
        """
        components = [c.strip() for c in autoskip_selector]
        if "node:{}".format(self.name) in components:
            return True
        for group in self.groups:
            if "group:{}".format(group.name) in components:
                return True
        return False

    def group_membership_hash(self):
        return hash_statedict(sorted(names(self.groups)))

    @property
    def immediate_groups(self):
        result = set()
        for group_name in self._attributes.get('groups', set()):
            try:
                result.add(self.repo.get_group(group_name))
            except NoSuchGroup:
                raise RepositoryError(_(
                    "Node '{node}' has '{group}' listed as a group, "
                    "but no such group could be found."
                ).format(
                    node=self.name,
                    group=group_name,
                ))
        for group in self.repo.groups:
            if group in result:
                continue
            elif self in group._nodes_from_members:
                result.add(self.repo.get_group(group.name))
            else:
                for pattern in group._member_patterns:
                    if pattern.search(self.name) is not None:
                        result.add(self.repo.get_group(group.name))
        return result

    @cached_property_set
    @io.job_wrapper(_("{}  determining groups").format(bold("{0.name}")))
    def groups(self):
        for group in self.immediate_groups:
            yield group
            for parent_group in group.parent_groups:
                # these are not just the *immediate* parent groups
                yield parent_group

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

    @cached_property_set
    def items(self):
        items = {}
        if not self.dummy:
            for bundle in self.bundles:
                for item in bundle.items:
                    if item.id in items:
                        raise BundleError(_(
                            "duplicate definition of {item} in bundles '{bundle1}' and '{bundle2}'"
                        ).format(
                            item=item.id,
                            bundle1=item.bundle.name,
                            bundle2=items[item.id].bundle.name,
                        ))
                    else:
                        items[item.id] = item
        return items.values()

    @cached_property
    def magic_number(self):
        return int(md5(self.name.encode('UTF-8')).hexdigest(), 16)

    def check_connection(self):
        try:
            # Running "true" is meant to catch connection errors early,
            # but this only works on UNIX-y systems (i.e., not k8s).
            if self.os in self.OS_FAMILY_UNIX:
                self.run("true")
            elif self.os == 'routeros':
                self.run_routeros("/nothing")
        except (RemoteException, TransportException) as exc:
            io.stdout(_("{x} {node}  Connection error: {msg}").format(
                msg=exc,
                node=bold(self.name),
                x=red("!"),
            ))
            return False
        else:
            return True

    def apply(
        self,
        autoskip_selector=(),
        autoonly_selector=(),
        interactive=False,
        force=False,
        show_diff=True,
        show_skipped_items=True,
        skip_list=(),
        workers=4,
    ):
        if not list(self.items):
            io.stdout(_("{x} {node}  has no items").format(
                node=bold(self.name),
                x=yellow("»"),
            ))
            return None

        if self.covered_by_autoskip_selector(autoskip_selector):
            io.stdout(_("{x} {node}  skipped by --skip").format(
                node=bold(self.name),
                x=yellow("»"),
            ))
            return None

        if self.name in skip_list:
            io.stdout(_("{x} {node}  skipped by --resume-file").format(
                node=bold(self.name),
                x=yellow("»"),
            ))
            return None

        try:
            self.repo.hooks.node_apply_start(
                self.repo,
                self,
                interactive=interactive,
            )
        except SkipNode as exc:
            io.stdout(_("{x} {node}  skipped by hook ({reason})").format(
                node=bold(self.name),
                reason=str(exc) or _("no reason given"),
                x=yellow("»"),
            ))
            return None

        start = datetime.now()
        io.stdout(_("{x} {node}  {started} at {time}").format(
            node=bold(self.name),
            started=bold(_("started")),
            time=start.strftime("%Y-%m-%d %H:%M:%S"),
            x=blue("i"),
        ))

        error = None
        if not self.check_connection():
            error = _("Connection error (details above)")
            item_results = []
        else:
            try:
                with NodeLock(self, interactive=interactive, ignore=force) as lock:
                    item_results = apply_items(
                        self,
                        autoskip_selector=autoskip_selector,
                        autoonly_selector=autoonly_selector,
                        my_soft_locks=lock.my_soft_locks,
                        other_peoples_soft_locks=lock.other_peoples_soft_locks,
                        workers=workers,
                        interactive=interactive,
                        show_diff=show_diff,
                        show_skipped_items=show_skipped_items,
                    )
            except NodeLockedException as e:
                if not interactive:
                    io.stderr(_(
                        "{x} {node} already locked by {user} at {date} ({duration} ago, "
                        "`bw apply -f` to override)"
                    ).format(
                        date=bold(e.args[0]['date']),
                        duration=e.args[0]['duration'],
                        node=bold(self.name),
                        user=bold(e.args[0]['user']),
                        x=red("!"),
                    ))
                error = _("Node locked (details above)")
                item_results = []
        result = ApplyResult(self, item_results)
        result.start = start
        result.end = datetime.now()

        io.stdout(_("{x} {node}  {completed} after {time}  ({stats})").format(
            completed=bold(_("completed")),
            node=bold(self.name),
            stats=format_node_result(result),
            time=format_duration(result.end - start),
            x=blue("i"),
        ))

        self.repo.hooks.node_apply_end(
            self.repo,
            self,
            duration=result.duration,
            interactive=interactive,
            result=result,
        )

        if error:
            raise GracefulApplyException(error)
        else:
            return result

    def download(self, remote_path, local_path):
        return operations.download(
            self.hostname,
            remote_path,
            local_path,
            add_host_keys=self._add_host_keys,
            username=self.username,
            wrapper_inner=self.cmd_wrapper_inner,
            wrapper_outer=self.cmd_wrapper_outer,
        )

    def get_item(self, item_id):
        return find_item(item_id, self.items)

    @property
    def metadata(self):
        return self.repo._metadata_proxy_for_node(self.name)

    def metadata_get(self, *args, **kwargs):
        # TODO remove in 5.0
        return self.metadata.get(*args, _backwards_compatibility_default=False, **kwargs)

    def metadata_hash(self):
        return hash_metadata(self.metadata)

    @property
    def metadata_defaults(self):
        for bundle in self.bundles:
            if bundle._metadata_defaults_and_reactors[0]:
                yield (
                    "metadata_defaults:{}".format(bundle.name),
                    bundle._metadata_defaults_and_reactors[0],
                )

    @property
    def metadata_reactors(self):
        for bundle in self.bundles:
            for reactor in bundle._metadata_defaults_and_reactors[1]:
                yield (
                    "metadata_reactor:{}.{}".format(
                        bundle.name,
                        reactor.__name__,
                    ),
                    reactor,
                )

    @property
    def partial_metadata(self):
        """
        Deprecated, remove in 5.0.0
        """
        return self.metadata

    def rename(self, new_name):
        if not self.is_toml:
            raise ValueError(_(
                "{node} cannot be renamed: not in TOML format"
            ).format(node=self.name))
        new_path = join(dirname(self.file_path), f"{new_name}.toml")
        rename(self.file_path, new_path)
        self.file_path = new_path
        self.name = new_name

    def run(self, command, data_stdin=None, may_fail=False, log_output=False, user="root"):
        assert self.os in self.OS_FAMILY_UNIX

        if log_output:
            def log_function(msg):
                io.stdout("{x} {node}  {msg}".format(
                    node=bold(self.name),
                    msg=force_text(msg).rstrip("\n"),
                    x=cyan("›"),
                ))
        else:
            log_function = None

        if not self._ssh_conn_established:
            # Sometimes we're opening SSH connections to a node too fast
            # for OpenSSH to establish the ControlMaster socket for the
            # second and following connections to use.
            # To prevent this, we just wait until a first dummy command
            # has completed on the node before trying to reuse the
            # multiplexed connection.
            if self._ssh_first_conn_lock.acquire(False):
                self.repo.hooks.node_ssh_connect(self.repo, self)
                try:
                    with io.job(_("{}  establishing connection...").format(bold(self.name))):
                        operations.run(
                            self.hostname,
                            "true",
                            add_host_keys=self._add_host_keys,
                            username=self.username,
                        )
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
            add_host_keys=self._add_host_keys,
            data_stdin=data_stdin,
            ignore_failure=may_fail,
            log_function=log_function,
            username=self.username,
            wrapper_inner=self.cmd_wrapper_inner,
            wrapper_outer=self.cmd_wrapper_outer,
            user=user,
        )

    def run_ipmitool(self, command, log_output=False):
        if not (self.ipmi_hostname and self.ipmi_username and self.ipmi_password):
            raise ValueError(_("node {} has no or invalid ipmi configuration").format(self.name))

        if log_output:
            def log_function(msg):
                io.stdout("{x} {node}  {msg}".format(
                    node=bold(self.name),
                    msg=force_text(msg).rstrip("\n"),
                    x=cyan("›"),
                ))
        else:
            log_function = None

        return operations.run_ipmitool(
            # these might be Faults
            self.ipmi_hostname,
            str(self.ipmi_username),
            str(self.ipmi_password),
            command,
            interface=self.ipmi_interface,
            log_function=log_function,
        )

    def run_routeros(self, *command):
        assert self.os == 'routeros'
        return operations.run_routeros(
            self.hostname,
            self.username,
            self.password,
            *command,
        )

    @property
    def is_toml(self):
        return self.file_path and self.file_path.endswith(".toml")

    @cached_property
    def toml(self):
        if not self.is_toml:
            raise ValueError(_("node {} not in TOML format").format(self.name))
        return toml_parse(get_file_contents(self.file_path))

    def toml_save(self):
        try:
            toml_doc = self.toml
        except ValueError:
            attributes = self._attributes.copy()
            del attributes['file_path']
            toml_doc = dict_to_toml(attributes)
            self.file_path = join(self.repo.path, "nodes", self.name + ".toml")
        if not exists(join(self.repo.path, "nodes")):
            mkdir(join(self.repo.path, "nodes"))
        with open(self.file_path, 'w') as f:
            f.write(toml_clean(toml_dump(toml_doc)))

    def toml_set(self, path, value):
        if not isinstance(path, tuple):
            path = path.split("/")
        set_key_at_path(self.toml, path, value)

    def upload(self, local_path, remote_path, mode=None, owner="", group="", may_fail=False):
        assert self.os in self.OS_FAMILY_UNIX
        return operations.upload(
            self.hostname,
            local_path,
            remote_path,
            add_host_keys=self._add_host_keys,
            group=group,
            mode=mode,
            owner=owner,
            ignore_failure=may_fail,
            username=self.username,
            wrapper_inner=self.cmd_wrapper_inner,
            wrapper_outer=self.cmd_wrapper_outer,
        )

    def verify(
        self,
        autoskip_selector=(),
        autoonly_selector=(),
        show_all=False,
        show_diff=True,
        workers=4,
    ):
        result = []
        start = datetime.now()

        if not self.items:
            io.stdout(_("{x} {node}  has no items").format(node=bold(self.name), x=yellow("!")))
        elif not self.check_connection():
            io.stdout(_("{x} {node}  Connection error (details above)").format(node=bold(self.name), x=red("!")))
        else:
            result = verify_items(
                self,
                autoskip_selector=autoskip_selector,
                autoonly_selector=autoonly_selector,
                show_all=show_all,
                show_diff=show_diff,
                workers=workers,
            )

        return {
            'good': result.count(True),
            'bad': result.count(False),
            'unknown': result.count(None),
            'duration': datetime.now() - start,
        }


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
    method.__name__ = "_group_attr_{}".format(attr)  # required for cached_property
    return cached_property(method)

for attr, default in GROUP_ATTR_DEFAULTS.items():
    setattr(Node, attr, build_attr_property(attr, default))


def verify_items(
    node,
    autoskip_selector=(),
    autoonly_selector=(),
    show_all=False,
    show_diff=True,
    workers=1,
):
    items = []
    for item in node.items:
        if not item.triggered:
            items.append(item)
        else:
            io.progress_advance()

    try:
        # See comment in node.apply().
        if node.os in node.OS_FAMILY_UNIX:
            node.run("true")
    except (RemoteException, TransportException) as exc:
        io.stdout(_("{x} {node}  Connection error: {msg}").format(
            msg=exc,
            node=bold(node.name),
            x=red("!"),
        ))
        for item in items:
            io.progress_advance()
        return [None for item in items]

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
                    io.progress_advance()
                    io.stdout(_("{x} {node}  {bundle}  {item}  ({msg})").format(
                        bundle=bold(item.bundle.name),
                        item=item.id,
                        msg=yellow(_("Fault unavailable")),
                        node=bold(node.name),
                        x=yellow("»"),
                    ))
            else:
                return {
                    'task_id': node.name + ":" + item.bundle.name + ":" + item.id,
                    'target': item.verify,
                    'kwargs': {
                        'autoskip_selector': autoskip_selector,
                        'autoonly_selector': autoonly_selector,
                    },
                }

    def handle_exception(task_id, exception, traceback):
        node_name, bundle_name, item_id = task_id.split(":", 2)
        io.progress_advance()
        if isinstance(exception, (ItemSkipped, NotImplementedError)):
            pass
        else:
            # Unlike with `bw apply`, it is OK for `bw verify` to encounter
            # exceptions when getting an item's status. `bw verify` doesn't
            # care about dependencies and therefore cannot know that looking
            # up a database user requires the database to be installed in
            # the first place.
            item = node.get_item(task_id.split(":", 2)[2])
            output = _("{x} {node}  {bundle}  {item}  (unable to get status)\n").format(
                bundle=bold(bundle_name),
                item=item_id,
                node=bold(node_name),
                x=bold(cyan("?")),
            )
            output += prefix_lines(traceback, cyan("│ "))
            output += prefix_lines(repr(exception), cyan("│ "))
            if item._command_results:
                output += format_item_command_results(item._command_results)
                # free up memory
                del item._command_results
            io.stderr(output)
        return None  # count this result as "unknown"

    def handle_result(task_id, return_value, duration):
        io.progress_advance()
        unless_result, item_status, display = return_value
        node_name, bundle_name, item_id = task_id.split(":", 2)
        if not unless_result and not item_status.correct:
            if item_status.must_be_created:
                details_text = red(_("missing"))
            elif item_status.must_be_deleted:
                details_text = red(_("found"))
            elif show_diff:
                details_text = ""
            else:
                details_text = ", ".join(sorted(display[2]))
            if show_diff:
                diff = "\n"
                if item_status.must_be_created:
                    diff += dict_to_text(display, value_color=green)
                elif item_status.must_be_deleted:
                    diff += dict_to_text(display, value_color=red)
                else:
                    diff += diff_dict(display[1], display[0], skip_missing_in_target=True)
                output = "{x} {node}  {bundle}  {item}  {details}\n".format(
                    bundle=bold(bundle_name),
                    details=details_text,
                    item=item_id,
                    node=bold(node_name),
                    x=red("✘"),
                )
                output += prefix_lines(diff, red('│ '))
                io.stderr(output + red("╵"))
            else:
                io.stderr("{x} {node}  {bundle}  {item}  {details}".format(
                    bundle=bold(bundle_name),
                    details=details_text,
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
        handle_exception=handle_exception,
        pool_id="verify_{}".format(node.name),
        workers=workers,
    )
    return worker_pool.run()
