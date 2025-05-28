from argparse import ArgumentParser, RawTextHelpFormatter, SUPPRESS
from os import environ, getcwd
from os.path import join

from .. import VERSION_STRING
from ..utils.cmdline import (DEFAULT_item_workers, DEFAULT_node_workers,
                             DEFAULT_softlock_expiry, HELP_get_target_nodes,
                             HELP_item_workers, HELP_node_workers,
                             HELP_softlock_expiry)
from ..utils.text import mark_for_translation as _
from ..utils.text import remove_prefix
from .apply import bw_apply
from .debug import bw_debug
from .diff import bw_diff
from .generate_completions import bw_generate_completions
from .groups import bw_groups
from .hash import bw_hash
from .ipmi import bw_ipmi
from .items import bw_items
from .lock import bw_lock_add, bw_lock_remove, bw_lock_show
from .metadata import bw_metadata
from .nodes import bw_nodes
from .plot import bw_plot_group, bw_plot_node, bw_plot_node_groups, bw_plot_reactors
from .pw import bw_pw
from .repo import bw_repo_bundle_create, bw_repo_create
from .run import bw_run
from .stats import bw_stats
from .test import bw_test
from .verify import bw_verify
from .zen import bw_zen

try:
    from argcomplete import autocomplete, warn

    shell_completion = True
except ImportError:
    shell_completion = False


class TargetCompleter:
    """Completer for bw targets, which can be used by argcomplete"""

    def __call__(self, parsed_args, **kwargs):
        try:
            # warn(kwargs)  # For development and debugging
            compl_file = join(parsed_args.repo_path, '.bw_shell_completion_targets')
            with open(compl_file) as f:
                return [
                    remove_prefix(remove_prefix(line, 'node:'), 'group:')
                    for line in f.read().splitlines()
                ]
        except FileNotFoundError:
            return []
        except Exception as exc:
            warn(f'Reading from target completion file failed: {repr(exc)}')
            return []


def build_parser_bw():
    parser = ArgumentParser(
        prog="bw",
        description=_("BundleWrap - Config Management with Python"),
    )
    parser.add_argument(
        "-a",
        "--add-host-keys",
        action='store_true',
        default=False,
        dest='add_ssh_host_keys',
        help=_("set StrictHostKeyChecking=no instead of yes for SSH"),
    )
    parser.add_argument(
        "-d",
        "--debug",
        action='store_true',
        default=False,
        dest='debug',
        help=_("print debugging info"),
    )
    parser.add_argument(
        "-r",
        "--repo-path",
        default=environ.get('BW_REPO_PATH', getcwd()),
        dest='repo_path',
        help=_("Look for repository at this path (defaults to current working directory)"),
        metavar=_("DIRECTORY"),
        type=str,
    )
    # hidden option to dump profiling info, can be inpected with
    # SnakeViz or whatever
    parser.add_argument(
        "--profile",
        default=None,
        dest='profile',
        help=SUPPRESS,
        metavar=_("FILE"),
        type=str,
    )
    parser.add_argument(
        "--version",
        action='version',
        version=VERSION_STRING,
    )
    subparsers = parser.add_subparsers(
        title=_("subcommands"),
        help=_("use 'bw <subcommand> --help' for more info"),
    )

    # bw apply
    help_apply = _("Applies the configuration defined in your repository to your nodes")
    parser_apply = subparsers.add_parser(
        "apply",
        description=help_apply,
        help=help_apply,
        formatter_class=RawTextHelpFormatter,  # for HELP_get_target_nodes
    )
    parser_apply.set_defaults(func=bw_apply)
    targets_apply = parser_apply.add_argument(
        'targets',
        metavar=_("TARGET"),
        nargs='+',
        type=str,
        help=HELP_get_target_nodes,
    )
    if shell_completion:
        targets_apply.completer = TargetCompleter()

    parser_apply.add_argument(
        "-D",
        "--no-diff",
        action='store_false',
        dest='show_diff',
        help=_("hide diff for incorrect items when NOT using --interactive"),
    )
    parser_apply.add_argument(
        "-f",
        "--force",
        action='store_true',
        default=False,
        dest='force',
        help=_("ignore existing hard node locks"),
    )
    parser_apply.add_argument(
        "-i",
        "--interactive",
        action='store_true',
        default=False,
        dest='interactive',
        help=_("ask before applying each item"),
    )
    parser_apply.add_argument(
        "-o",
        "--only",
        default=[],
        dest='autoonly',
        help=_("""skip all items not matching any SELECTOR:

file:/my_path     # this specific item
tag:my_tag        # items with this tag
bundle:my_bundle  # items in this bundle

dependencies of selected items will NOT be skipped
        """),
        metavar=_("SELECTOR"),
        nargs='+',
        type=str,
    )
    parser_apply.add_argument(
        "-p",
        "--parallel-nodes",
        default=DEFAULT_node_workers,
        dest='node_workers',
        help=HELP_node_workers,
        type=int,
    )
    parser_apply.add_argument(
        "-P",
        "--parallel-items",
        default=DEFAULT_item_workers,
        dest='item_workers',
        help=HELP_item_workers,
        type=int,
    )
    parser_apply.add_argument(
        "-s",
        "--skip",
        default=[],
        dest='autoskip',
        help=_("""skip items matching any SELECTOR:

file:/my_path     # this specific item
tag:my_tag        # items with this tag
bundle:my_bundle  # items in this bundle
        """),
        metavar=_("SELECTOR"),
        nargs='+',
        type=str,
    )
    parser_apply.add_argument(
        "-S",
        "--no-summary",
        action='store_false',
        dest='summary',
        help=_("don't show stats summary"),
    )
    parser_apply.add_argument(
        "--no-skipped-items",
        action='store_false',
        dest='show_skipped_items',
        help=_("don't show skipped items"),
    )
    parser_apply.add_argument(
        "-r",
        "--resume-file",
        default=None,
        dest='resume_file',
        help=_(
            "path to a file that a list of completed nodes will be added to; "
            "if the file already exists, any nodes therein will be skipped"
        ),
        metavar=_("PATH"),
        type=str,
    )

    # bw debug
    help_debug = _("Start an interactive Python shell for this repository")
    parser_debug = subparsers.add_parser("debug", description=help_debug, help=help_debug)
    parser_debug.set_defaults(func=bw_debug)
    parser_debug.add_argument(
        "-c",
        "--command",
        default=None,
        dest='command',
        metavar=_("COMMAND"),
        required=False,
        type=str,
        help=_("command to execute in lieu of REPL"),
    )
    parser_debug.add_argument(
        "-n",
        "--node",
        default=None,
        dest='node',
        metavar=_("NODE"),
        required=False,
        type=str,
        help=_("name of node to inspect"),
    )

    # bw diff
    help_diff = _("Show differences between nodes")
    parser_diff = subparsers.add_parser(
        "diff",
        description=help_diff,
        help=help_diff,
        formatter_class=RawTextHelpFormatter,  # for HELP_get_target_nodes
    )
    parser_diff.set_defaults(func=bw_diff)
    parser_diff.add_argument(
        "-b",
        "--branch",
        default=None,
        dest='branch',
        metavar=_("REV"),
        required=False,
        type=str,
        help=_("compare with this git rev instead (requires clean working dir)"),
    )
    parser_diff.add_argument(
        "-c",
        "--cmd-change",
        default=None,
        dest='cmd_change',
        metavar=_("CMD_CHANGE"),
        required=False,
        type=str,
        help=_("command to execute between taking metadata snapshots (e.g., change Git branch)"),
    )
    parser_diff.add_argument(
        "-r",
        "--cmd-reset",
        default=None,
        dest='cmd_reset',
        metavar=_("CMD_RESET"),
        required=False,
        type=str,
        help=_("command to execute when finished (e.g., switch back to original Git branch)"),
    )
    parser_diff.add_argument(
        "-p",
        "--prompt",
        action='store_true',
        default=False,
        dest='prompt',
        help=_("interactively ask for user to make changes"),
    )
    parser_diff.add_argument(
        "-i",
        "--item",
        default=None,
        dest='item',
        metavar=_("ITEM"),
        required=False,
        type=str,
        help=_("compare this specific item between nodes"),
    )
    parser_diff.add_argument(
        "-m",
        "--metadata",
        action='store_true',
        default=False,
        dest='metadata',
        help=_("compare metadata instead of configuration"),
    )
    targets_diff = parser_diff.add_argument(
        'targets',
        metavar=_("TARGET"),
        nargs='+',
        type=str,
        help=HELP_get_target_nodes,
    )
    if shell_completion:
        targets_diff.completer = TargetCompleter()

    # bw groups
    help_groups = _("Lists groups in this repository")
    parser_groups = subparsers.add_parser("groups", description=help_groups, help=help_groups)
    parser_groups.set_defaults(func=bw_groups)
    parser_groups.add_argument(
        "-a", "--attrs",
        dest='attrs',
        metavar=_("ATTR"),
        nargs='+',
        type=str,
        help=_("show table with the given attributes for each group "
               "(e.g. 'all', 'members', 'os', ...)"),
    )
    parser_groups.add_argument(
        "-i",
        "--inline",
        action='store_true',
        dest='inline',
        help=_("keep lists on a single line (for grep)"),
    )
    parser_groups.add_argument(
        'groups',
        default=None,
        metavar=_("GROUP"),
        nargs='*',
        type=str,
        help=_("show the given groups (and their subgroups, unless --attrs is used)"),
    )

    # bw hash
    help_hash = _("Shows a SHA1 hash that summarizes the entire configuration for this repo, node, group, or item.")
    parser_hash = subparsers.add_parser("hash", description=help_hash, help=help_hash)
    parser_hash.set_defaults(func=bw_hash)
    parser_hash.add_argument(
        "-d",
        "--dict",
        action='store_true',
        default=False,
        dest='dict',
        help=_("instead show the data this hash is derived from"),
    )
    parser_hash.add_argument(
        "-g",
        "--group",
        action='store_true',
        default=False,
        dest='group_membership',
        help=_("hash group membership instead of configuration"),
    )
    parser_hash.add_argument(
        "-m",
        "--metadata",
        action='store_true',
        default=False,
        dest='metadata',
        help=_("hash metadata instead of configuration (not available for items)"),
    )
    parser_hash.add_argument(
        'node_or_group',
        metavar=_("NODE|GROUP"),
        type=str,
        nargs='?',
        help=_("show config hash for this node or group"),
    )
    parser_hash.add_argument(
        'item',
        metavar=_("ITEM"),
        type=str,
        nargs='?',
        help=_("show config hash for this item on the given node"),
    )

    # bw ipmi
    help_ipmi = _("Run 'ipmitool' on the ipmi interface of a specific node")
    parser_ipmi = subparsers.add_parser(
        "ipmi",
        description=help_ipmi,
        help=help_ipmi,
        formatter_class=RawTextHelpFormatter,  # for HELP_get_target_nodes
    )
    parser_ipmi.set_defaults(func=bw_ipmi)
    targets_ipmi = parser_ipmi.add_argument(
        'targets',
        metavar=_("TARGET"),
        nargs='+',
        type=str,
        help=HELP_get_target_nodes,
    )
    if shell_completion:
        targets_ipmi.completer = TargetCompleter()

    parser_ipmi.add_argument(
        'command',
        metavar=_("COMMAND"),
        type=str,
        help=_("command to run"),
    )
    parser_ipmi.add_argument(
        "-p",
        "--parallel-nodes",
        default=DEFAULT_node_workers,
        dest='node_workers',
        help=HELP_node_workers,
        type=int,
    )

    # bw items
    help_items = _("List and preview items for a specific node")
    parser_items = subparsers.add_parser("items", description=help_items, help=help_items)
    parser_items.set_defaults(func=bw_items)
    parser_items.add_argument(
        'node',
        metavar=_("NODE"),
        type=str,
        help=_("list items for this node"),
    )
    parser_items.add_argument(
        'item',
        metavar=_("ITEM"),
        nargs='?',
        type=str,
        help=_("show configuration for this item"),
    )
    parser_items.add_argument(
        'attr',
        metavar=_("ATTRIBUTE"),
        nargs='?',
        type=str,
        help=_("show only this item attribute"),
    )
    parser_items.add_argument(
        "-f",
        "--preview",
        "--file-preview",  # TODO 4.0 remove
        action='store_true',
        dest='preview',
        help=_("print preview of given ITEM"),
    )
    parser_items.add_argument(
        "-w",
        "--write-file-previews",
        default=None,
        dest='file_preview_path',
        metavar=_("DIRECTORY"),
        required=False,
        type=str,
        help=_("create DIRECTORY and fill it with rendered file previews"),
    )
    parser_items.add_argument(
        "--attrs",
        action='store_true',
        dest='show_attrs',
        help=_("show internal item attributes"),
    )
    parser_items.add_argument(
        "--blame",
        action='store_true',
        dest='blame',
        help=_("show information on which bundle defines each item"),
    )
    parser_items.add_argument(
        "--repr",
        action='store_true',
        dest='show_repr',
        help=_("show more verbose representation of each item"),
    )
    parser_items.add_argument(
        "--state",
        action='store_true',
        dest='show_sdict',
        help=_("show actual item status on node instead of should-be configuration"),
    )

    # bw lock
    help_lock = _("Manage locks on nodes used to prevent collisions between BundleWrap users")
    parser_lock = subparsers.add_parser(
        "lock",
        description=help_lock,
        help=help_lock,
    )
    parser_lock_subparsers = parser_lock.add_subparsers()

    # bw lock add
    help_lock_add = _("Add a new lock to one or more nodes")
    parser_lock_add = parser_lock_subparsers.add_parser(
        "add",
        description=help_lock_add,
        help=help_lock_add,
        formatter_class=RawTextHelpFormatter,  # for HELP_get_target_nodes
    )
    parser_lock_add.set_defaults(func=bw_lock_add)
    targets_lock_add = parser_lock_add.add_argument(
        'targets',
        metavar=_("TARGET"),
        nargs='+',
        type=str,
        help=HELP_get_target_nodes,
    )
    if shell_completion:
        targets_lock_add.completer = TargetCompleter()

    parser_lock_add.add_argument(
        "-c",
        "--comment",
        default="",
        dest='comment',
        help=_("brief description of the purpose of the lock"),
        type=str,
    )
    parser_lock_add.add_argument(
        "-e",
        "--expires-in",
        default=DEFAULT_softlock_expiry,
        dest='expiry',
        help=HELP_softlock_expiry,
        type=str,
    )
    parser_lock_add.add_argument(
        "-i",
        "--items",
        default=["*"],
        dest='items',
        help=_("""lock only items matching any SELECTOR:

file:/my_path     # this specific item
tag:my_tag        # items with this tag
bundle:my_bundle  # items in this bundle
        """),
        metavar=_("SELECTOR"),
        nargs='+',
        type=str,
    )
    parser_lock_add.add_argument(
        "-p",
        "--parallel-nodes",
        default=DEFAULT_node_workers,
        dest='node_workers',
        help=HELP_node_workers,
        type=int,
    )

    # bw lock remove
    help_lock_remove = _("Remove a lock from a node")
    parser_lock_remove = parser_lock_subparsers.add_parser(
        "remove",
        description=help_lock_remove,
        help=help_lock_remove,
        formatter_class=RawTextHelpFormatter,  # for HELP_get_target_nodes
    )
    parser_lock_remove.set_defaults(func=bw_lock_remove)
    targets_lock_remove = parser_lock_remove.add_argument(
        'targets',
        metavar=_("TARGET"),
        nargs='+',
        type=str,
        help=HELP_get_target_nodes,
    )
    if shell_completion:
        targets_lock_remove.completer = TargetCompleter()

    parser_lock_remove.add_argument(
        'lock_id',
        metavar=_("LOCK_ID"),
        type=str,
        help=_("ID of the lock to remove (obtained with `bw lock show`)"),
    )
    parser_lock_remove.add_argument(
        "-p",
        "--parallel-nodes",
        default=DEFAULT_node_workers,
        dest='node_workers',
        help=HELP_node_workers,
        type=int,
    )

    # bw lock show
    help_lock_show = _("Show details of locks present on a node")
    parser_lock_show = parser_lock_subparsers.add_parser(
        "show",
        description=help_lock_show,
        help=help_lock_show,
        formatter_class=RawTextHelpFormatter,  # for HELP_get_target_nodes
    )
    parser_lock_show.set_defaults(func=bw_lock_show)
    targets_lock_show = parser_lock_show.add_argument(
        'targets',
        metavar=_("TARGETS"),
        nargs='+',
        type=str,
        help=HELP_get_target_nodes,
    )
    if shell_completion:
        targets_lock_show.completer = TargetCompleter()

    parser_lock_show.add_argument(
        "-i",
        "--items",
        default=None,
        dest='items',
        help=_("""check locks against items matching any SELECTOR:

file:/my_path     # this specific item
tag:my_tag        # items with this tag
bundle:my_bundle  # items in this bundle

will exit with code 47 if any matching items are locked
        """),
        metavar=_("SELECTOR"),
        nargs='+',
        type=str,
    )
    parser_lock_show.add_argument(
        "-p",
        "--parallel-nodes",
        default=DEFAULT_node_workers,
        dest='node_workers',
        help=HELP_node_workers,
        type=int,
    )
    parser_lock_show.add_argument(
        "--hide-not-locked",
        help=_("hide table rows for nodes without any locks "
               "(defaults to False)"),
        action='store_true',
    )

    # bw metadata
    help_metadata = (
        "View a JSON representation of a node's metadata (defaults blue, reactors green, groups yellow, node red, uncolored if mixed-source) or a table of selected metadata keys from multiple nodes")
    parser_metadata = subparsers.add_parser(
        "metadata",
        description=help_metadata,
        help=help_metadata,
        formatter_class=RawTextHelpFormatter,
    )
    parser_metadata.set_defaults(func=bw_metadata)
    targets_metadata = parser_metadata.add_argument(
        'targets',
        metavar=_("TARGET"),
        nargs='+',
        type=str,
        help=HELP_get_target_nodes,
    )
    if shell_completion:
        targets_metadata.completer = TargetCompleter()

    parser_metadata.add_argument(
        "-k", "--keys",
        default=[],
        dest='keys',
        metavar=_("KEY"),
        nargs='*',
        type=str,
        help=_(
            "show only partial metadata from the given key paths (e.g. `bw metadata mynode -k users/jdoe` to show `mynode.metadata['users']['jdoe']`)"),
    )
    parser_metadata.add_argument(
        "-b", "--blame",
        action='store_true',
        dest='blame',
        help=_("show where each piece of metadata comes from"),
    )
    parser_metadata.add_argument(
        "-D", "--hide-defaults",
        action='store_true',
        dest='hide_defaults',
        help=_("hide values set by defaults in metadata.py"),
    )
    parser_metadata.add_argument(
        "-G", "--hide-groups",
        action='store_true',
        dest='hide_groups',
        help=_("hide values set in groups.py"),
    )
    parser_metadata.add_argument(
        "-N", "--hide-node",
        action='store_true',
        dest='hide_node',
        help=_("hide values set in nodes.py"),
    )
    parser_metadata.add_argument(
        "-R", "--hide-reactors",
        action='store_true',
        dest='hide_reactors',
        help=_("hide values set by reactors in metadata.py"),
    )
    parser_metadata.add_argument(
        "-f", "--resolve-faults",
        action='store_true',
        dest='resolve_faults',
        help=_("resolve Faults; careful, might contain sensitive data"),
    )

    # bw nodes
    help_nodes = _("List nodes in this repository")
    parser_nodes = subparsers.add_parser(
        "nodes",
        description=help_nodes,
        help=help_nodes,
        formatter_class=RawTextHelpFormatter,  # for HELP_get_target_nodes
    )
    parser_nodes.set_defaults(func=bw_nodes)
    parser_nodes.add_argument(
        "-a",
        "--attrs",
        default=None,
        dest='attrs',
        metavar=_("ATTR"),
        nargs='+',
        type=str,
        help=_("show table with the given attributes for each node "
               "(e.g. 'all', 'groups', 'bundles', 'hostname', 'os', ...)"),
    )
    parser_nodes.add_argument(
        "-i",
        "--inline",
        action='store_true',
        dest='inline',
        help=_("keep lists on a single line (for grep)"),
    )
    parser_nodes.add_argument(
        "-p",
        "--parallel-nodes",
        default=DEFAULT_node_workers,
        dest='node_workers',
        help=HELP_node_workers,
        type=int,
    )
    targets_nodes = parser_nodes.add_argument(
        'targets',
        default=None,
        metavar=_("TARGET"),
        nargs='*',
        type=str,
        help=HELP_get_target_nodes,
    )
    if shell_completion:
        targets_nodes.completer = TargetCompleter()

    # bw plot
    help_plot = _("Generates DOT output that can be piped into `dot -Tsvg -ooutput.svg`. "
                  "The resulting output.svg can be viewed using most browsers.")
    parser_plot = subparsers.add_parser("plot", description=help_plot, help=help_plot)
    parser_plot_subparsers = parser_plot.add_subparsers()

    # bw plot group
    help_plot_group = _("Plot subgroups and node members for the given group "
                        "or the entire repository")
    parser_plot_subparsers_group = parser_plot_subparsers.add_parser(
        "group",
        description=help_plot_group,
        help=help_plot_group,
    )
    parser_plot_subparsers_group.set_defaults(func=bw_plot_group)
    parser_plot_subparsers_group.add_argument(
        'group',
        default=None,
        metavar=_("GROUP"),
        nargs='?',
        type=str,
        help=_("group to plot"),
    )
    parser_plot_subparsers_group.add_argument(
        "-N", "--no-nodes",
        action='store_false',
        dest='show_nodes',
        help=_("do not include nodes in output"),
    )

    # bw plot node
    help_plot_node = _(
        "Plot items and their dependencies for the given node. "
        "Color guide: "
        "needs in red, "
        "after in blue, "
        "before in yellow, "
        "needed_by in orange, "
        "auto in green, "
        "triggers in pink"
    )
    parser_plot_subparsers_node = parser_plot_subparsers.add_parser(
        "node",
        description=help_plot_node,
        help=help_plot_node,
    )
    parser_plot_subparsers_node.set_defaults(func=bw_plot_node)
    parser_plot_subparsers_node.add_argument(
        'node',
        metavar=_("NODE"),
        type=str,
        help=_("node to plot"),
    )
    parser_plot_subparsers_node.add_argument(
        "--no-cluster",
        action='store_false',
        dest='cluster',
        help=_("do not cluster items by bundle"),
    )
    parser_plot_subparsers_node.add_argument(
        "--no-depends-auto",
        action='store_false',
        dest='depends_auto',
        help=_("do not show auto-generated and trigger dependencies"),
    )
    # XXX Remove in bw 5
    parser_plot_subparsers_node.add_argument(
        "--no-depends-conc",
        action='store_false',
        dest='depends_concurrency',
        help=_("obsolete and ignored"),
    )
    parser_plot_subparsers_node.add_argument(
        "--no-depends-regular",
        action='store_false',
        dest='depends_regular',
        help=_("do not show after/needs dependencies"),
    )
    parser_plot_subparsers_node.add_argument(
        "--no-depends-reverse",
        action='store_false',
        dest='depends_reverse',
        help=_("do not show before/needed_by dependencies"),
    )

    # bw plot groups-for-node
    help_plot_node_groups = _("Show where a specific node gets its groups from")
    parser_plot_subparsers_node_groups = parser_plot_subparsers.add_parser(
        "groups-for-node",
        description=help_plot_node_groups,
        help=help_plot_node_groups,
    )
    parser_plot_subparsers_node_groups.set_defaults(func=bw_plot_node_groups)
    parser_plot_subparsers_node_groups.add_argument(
        'node',
        metavar=_("NODE"),
        type=str,
        help=_("node to plot"),
    )

    # bw plot reactors
    help_plot_node_reactors = _(
        "Show metadata reactor information flow for a node. "
        "Boxes are reactors, ovals are metadata paths provided or needed by reactors. "
        "Accesses to other nodes' metadata are truncated by default and shown in red. "
        "Numbers behind reactor names indicate how often the reactor result "
        "changed vs. how often the reactor was run (0/1 is perfect efficiency)."
    )
    parser_plot_subparsers_node_reactors = parser_plot_subparsers.add_parser(
        "reactors",
        description=help_plot_node_reactors,
        help=help_plot_node_reactors,
    )
    parser_plot_subparsers_node_reactors.set_defaults(func=bw_plot_reactors)
    parser_plot_subparsers_node_reactors.add_argument(
        'node',
        metavar=_("NODE"),
        type=str,
        help=_("node to plot"),
    )
    parser_plot_subparsers_node_reactors.add_argument(
        "-k", "--keys",
        default=[],
        dest='keys',
        metavar=_("KEY"),
        nargs='*',
        type=str,
        help=_(
            "request only partial metadata from the given key paths "
            "(e.g. `bw plot reactors mynode -k users/jdoe` "
            "to show `mynode.metadata['users']['jdoe']`)"
        ),
    )
    parser_plot_subparsers_node_reactors.add_argument(
        "-r"
        "--recursive",
        action='store_true',
        dest='recursive',
        help=_("do not truncate plot when crossing to other nodes (result might be huge)"),
    )

    # bw pw
    help_pw = _("Generate passwords and encrypt/decrypt secrets")
    parser_pw = subparsers.add_parser(
        "pw",
        description=help_pw,
        help=help_pw,
    )
    parser_pw.set_defaults(func=bw_pw)
    parser_pw.add_argument(
        'string',
        metavar=_("STRING"),
        type=str,
    )
    parser_pw.add_argument(
        "-b", "--bytes",
        action='store_true',
        dest='bytes',
        help=_("derive random bytes as base64 from STRING (`repo.vault.random_bytes_as_base64_for()`)"),
    )
    parser_pw.add_argument(
        "-d", "--decrypt",
        action='store_true',
        dest='decrypt',
        help=_("decrypt secret given as STRING (`repo.vault.decrypt()`)"),
    )
    parser_pw.add_argument(
        "-e", "--encrypt",
        action='store_true',
        dest='encrypt',
        help=_("encrypt secret in STRING (`repo.vault.encrypt()`)"),
    )
    parser_pw.add_argument(
        "-f", "--file",
        dest='file',
        metavar=_("TARGET_PATH"),
        type=str,
        help=_("treat STRING as source filename for -d and -e, write result to TARGET_PATH (relative to data/)"),
    )
    parser_pw.add_argument(
        "-H", "--human",
        action='store_true',
        dest='human',
        help=_("derive human-friendly password from STRING (`repo.vault.human_password_for()`)"),
    )
    parser_pw.add_argument(
        "-k", "--key",
        dest='key',
        metavar=_("NAME"),
        type=str,
        help=_(
            "which key from .secrets.cfg to use "
            "(defaults to 'encrypt' for -d and -e, 'generate' otherwise; "
            "overrides key name embedded in STRING)"
        ),
    )
    parser_pw.add_argument(
        "-l", "--length",
        default=32,
        dest='length',
        metavar=_("INT"),
        type=int,
        help=_("length for --password and --bytes (defaults to 32)"),
    )
    parser_pw.add_argument(
        "-p", "--password",
        action='store_true',
        dest='password',
        help=_("derive password from STRING (`repo.vault.password_for()`)"),
    )

    # bw repo
    help_repo = _("Various subcommands to manipulate your repository")
    parser_repo = subparsers.add_parser("repo", description=help_repo, help=help_repo)
    parser_repo_subparsers = parser_repo.add_subparsers()

    # bw repo bundle
    parser_repo_subparsers_bundle = parser_repo_subparsers.add_parser("bundle")
    parser_repo_subparsers_bundle_subparsers = parser_repo_subparsers_bundle.add_subparsers()

    # bw repo bundle create
    parser_repo_subparsers_bundle_create = \
        parser_repo_subparsers_bundle_subparsers.add_parser("create")
    parser_repo_subparsers_bundle_create.set_defaults(func=bw_repo_bundle_create)
    parser_repo_subparsers_bundle_create.add_argument(
        'bundle',
        metavar=_("BUNDLE"),
        type=str,
        help=_("name of bundle to create"),
    )

    # bw repo create
    parser_repo_subparsers_create = parser_repo_subparsers.add_parser("create")
    parser_repo_subparsers_create.set_defaults(func=bw_repo_create)

    # bw run
    help_run = _("Run a one-off command on a number of nodes")
    parser_run = subparsers.add_parser(
        "run",
        description=help_run,
        help=help_run,
        formatter_class=RawTextHelpFormatter,  # for HELP_get_target_nodes
    )
    parser_run.set_defaults(func=bw_run)
    targets_run = parser_run.add_argument(
        'targets',
        metavar=_("TARGET"),
        nargs='+',
        type=str,
        help=HELP_get_target_nodes,
    )
    if shell_completion:
        targets_run.completer = TargetCompleter()

    parser_run.add_argument(
        'command',
        metavar=_("COMMAND"),
        type=str,
        help=_("command to run"),
    )
    parser_run.add_argument(
        "--stderr-table",
        action='store_true',
        dest='stderr_table',
        help=_("include command stderr in stats table"),
    )
    parser_run.add_argument(
        "--stdout-table",
        action='store_true',
        dest='stdout_table',
        help=_("include command stdout in stats table"),
    )
    parser_run.add_argument(
        "-p",
        "--parallel-nodes",
        default=DEFAULT_node_workers,
        dest='node_workers',
        help=HELP_node_workers,
        type=int,
    )
    parser_run.add_argument(
        "-r",
        "--resume-file",
        default=None,
        dest='resume_file',
        help=_(
            "path to a file that a list of completed nodes will be added to; "
            "if the file already exists, any nodes therein will be skipped"
        ),
        metavar=_("PATH"),
        type=str,
    )
    parser_run.add_argument(
        "-S",
        "--no-summary",
        action='store_false',
        dest='summary',
        help=_("don't show stats summary"),
    )

    # bw stats
    help_stats = _("Show some statistics about your repository")
    parser_stats = subparsers.add_parser("stats", description=help_stats, help=help_stats)
    parser_stats.set_defaults(func=bw_stats)

    # bw test
    help_test = _("Test your repository for consistency "
                  "(you can use this with a CI tool like Jenkins). "
                  "If *any* options other than -i are given, *only* the "
                  "tests selected by those options will be run. Otherwise, a "
                  "default selection of tests will be run (that selection may "
                  "change in future releases). Currently, the default is -IJKMp "
                  "if specific nodes are given and -HIJKMSp if testing the "
                  "entire repo.")
    parser_test = subparsers.add_parser(
        "test",
        description=help_test,
        help=help_test,
        formatter_class=RawTextHelpFormatter,  # for HELP_get_target_nodes
    )
    parser_test.set_defaults(func=bw_test)
    targets_test = parser_test.add_argument(
        'targets',
        default=None,
        metavar=_("TARGET"),
        nargs='*',
        type=str,
        help=HELP_get_target_nodes + _("\n(defaults to all)"),
    )
    if shell_completion:
        targets_test.completer = TargetCompleter()

    parser_test.add_argument(
        "-d",
        "--config-determinism",
        default=0,
        dest='determinism_config',
        help=_("verify determinism of configuration by running `bw hash` N times "
               "and checking for consistent results (with N > 1)"),
        metavar="N",
        type=int,
    )
    parser_test.add_argument(
        "-e",
        "--empty-groups",
        action='store_true',
        dest='empty_groups',
        help=_("check for empty groups"),
    )
    parser_test.add_argument(
        "-H",
        "--hooks-repo",
        action='store_true',
        dest='hooks_repo',
        help=_("run repo-level test hooks"),
    )
    parser_test.add_argument(
        "-i",
        "--ignore-missing-faults",
        action='store_true',
        dest='ignore_missing_faults',
        help=_("do not fail when encountering a missing Fault"),
    )
    parser_test.add_argument(
        "-I",
        "--items",
        action='store_true',
        dest='items',
        help=_("run item-level tests (like rendering templates)"),
    )
    parser_test.add_argument(
        "-J",
        "--hooks-node",
        action='store_true',
        dest='hooks_node',
        help=_("run node-level test hooks"),
    )
    parser_test.add_argument(
        "-K",
        "--metadata-keys",
        action='store_true',
        dest='metadata_keys',
        help=_("validate metadata keys"),
    )
    parser_test.add_argument(
        "-m",
        "--metadata-determinism",
        default=0,
        dest='determinism_metadata',
        help=_("verify determinism of metadata by running `bw hash -m` N times "
               "and checking for consistent results (with N > 1)"),
        metavar="N",
        type=int,
    )
    parser_test.add_argument(
        "-M",
        "--metadata-conflicts",
        action='store_true',
        dest='metadata_conflicts',
        help=_("check for conflicting metadata keys in group metadata, reactors, and defaults"),
    )
    parser_test.add_argument(
        "-o",
        "--orphaned-bundles",
        action='store_true',
        dest='orphaned_bundles',
        help=_("check for bundles not assigned to any node"),
    )
    parser_test.add_argument(
        "-p",
        "--reactor-provides",
        action='store_true',
        dest='reactor_provides',
        help=_("check for reactors returning keys other than what they declared with @metadata_reactor.provides()"),
    )
    parser_test.add_argument(
        "-q",
        "--quiet",
        action='store_true',
        dest='quiet',
        help=_("don't show successful tests"),
    )
    parser_test.add_argument(
        "-S",
        "--subgroup-loops",
        action='store_true',
        dest='subgroup_loops',
        help=_("check for loops in subgroup hierarchies"),
    )

    # bw verify
    help_verify = _("Inspect the health or 'correctness' of a node without changing it")
    parser_verify = subparsers.add_parser(
        "verify",
        description=help_verify,
        help=help_verify,
        formatter_class=RawTextHelpFormatter,  # for HELP_get_target_nodes
    )
    parser_verify.set_defaults(func=bw_verify)
    targets_verify = parser_verify.add_argument(
        'targets',
        metavar=_("TARGET"),
        nargs='+',
        type=str,
        help=HELP_get_target_nodes,
    )
    if shell_completion:
        targets_verify.completer = TargetCompleter()

    parser_verify.add_argument(
        "-a",
        "--show-all",
        action='store_true',
        dest='show_all',
        help=_("show correct and skipped items as well as incorrect ones"),
    )
    parser_verify.add_argument(
        "-D",
        "--no-diff",
        action='store_false',
        dest='show_diff',
        help=_("hide diff for incorrect items"),
    )
    parser_verify.add_argument(
        "-o",
        "--only",
        default=[],
        dest='autoonly',
        help=_("""skip all items not matching any SELECTOR:

file:/my_path     # this specific item
tag:my_tag        # items with this tag
bundle:my_bundle  # items in this bundle
        """),
        metavar=_("SELECTOR"),
        nargs='+',
        type=str,
    )

    parser_verify.add_argument(
        "-p",
        "--parallel-nodes",
        default=DEFAULT_node_workers,
        dest='node_workers',
        help=HELP_node_workers,
        type=int,
    )
    parser_verify.add_argument(
        "-P",
        "--parallel-items",
        default=DEFAULT_item_workers,
        dest='item_workers',
        help=HELP_item_workers,
        type=int,
    )
    parser_verify.add_argument(
        "-s",
        "--skip",
        default=[],
        dest='autoskip',
        help=_("""skip items matching any SELECTOR:

file:/my_path     # this specific item
tag:my_tag        # items with this tag
bundle:my_bundle  # items in this bundle
        """),
        metavar=_("SELECTOR"),
        nargs='+',
        type=str,
    )
    parser_verify.add_argument(
        "-S",
        "--no-summary",
        action='store_false',
        dest='summary',
        help=_("don't show stats summary"),
    )

    # bw zen
    parser_zen = subparsers.add_parser("zen")
    parser_zen.set_defaults(func=bw_zen)

    if shell_completion:
        # bw generate_completions
        help_generate_completions = _("Generates the shell completion file")
        parser_generate_completions = subparsers.add_parser(
            "generate_completions",
            description=help_generate_completions,
            help=help_generate_completions,
        )
        parser_generate_completions.set_defaults(func=bw_generate_completions)

        autocomplete(parser)
    return parser
