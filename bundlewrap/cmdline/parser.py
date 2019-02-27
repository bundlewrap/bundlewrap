# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from argparse import ArgumentParser, SUPPRESS
from os import environ, getcwd

from .. import VERSION_STRING
from ..utils.text import mark_for_translation as _
from .apply import bw_apply
from .debug import bw_debug
from .groups import bw_groups
from .hash import bw_hash
from .items import bw_items
from .lock import bw_lock_add, bw_lock_remove, bw_lock_show
from .metadata import bw_metadata
from .nodes import bw_nodes
from .plot import bw_plot_group, bw_plot_node, bw_plot_node_groups
from .repo import bw_repo_bundle_create, bw_repo_create, bw_repo_plugin_install, \
    bw_repo_plugin_list, bw_repo_plugin_search, bw_repo_plugin_remove, bw_repo_plugin_update
from .run import bw_run
from .stats import bw_stats
from .test import bw_test
from .verify import bw_verify
from .zen import bw_zen


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
        "-A",
        "--adhoc-nodes",
        action='store_true',
        default=False,
        dest='adhoc_nodes',
        help=_(
            "treat unknown node names as adhoc 'virtual' nodes that receive configuration only "
            "through groups whose member_patterns match the node name given on the command line "
            "(which also has to be a resolvable hostname)"),
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
    parser_apply = subparsers.add_parser("apply", description=help_apply, help=help_apply)
    parser_apply.set_defaults(func=bw_apply)
    parser_apply.add_argument(
        'target',
        metavar=_("NODE1,NODE2,GROUP1,bundle:BUNDLE1..."),
        type=str,
        help=_("target nodes, groups and/or bundle selectors"),
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
        default="",
        dest='autoonly',
        help=_(
            "e.g. 'file:/foo,tag:foo,bundle:bar' "
            "to skip EVERYTHING BUT all instances of file:/foo "
            "and items with tag 'foo', "
            "or in bundle 'bar', "
            "or a dependency of any of these"
        ),
        metavar=_("SELECTOR"),
        type=str,
    )
    bw_apply_p_default = int(environ.get("BW_NODE_WORKERS", "4"))
    parser_apply.add_argument(
        "-p",
        "--parallel-nodes",
        default=bw_apply_p_default,
        dest='node_workers',
        help=_("number of nodes to apply to simultaneously "
               "(defaults to {})").format(bw_apply_p_default),
        type=int,
    )
    bw_apply_p_items_default = int(environ.get("BW_ITEM_WORKERS", "4"))
    parser_apply.add_argument(
        "-P",
        "--parallel-items",
        default=bw_apply_p_items_default,
        dest='item_workers',
        help=_("number of items to apply simultaneously on each node "
               "(defaults to {})").format(bw_apply_p_items_default),
        type=int,
    )
    parser_apply.add_argument(
        "-s",
        "--skip",
        default="",
        dest='autoskip',
        help=_(
            "e.g. 'file:/foo,tag:foo,bundle:bar' "
            "to skip all instances of file:/foo "
            "and items with tag 'foo', "
            "or in bundle 'bar'"
        ),
        metavar=_("SELECTOR"),
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

    # bw groups
    help_groups = _("Lists groups in this repository")
    parser_groups = subparsers.add_parser("groups", description=help_groups, help=help_groups)
    parser_groups.set_defaults(func=bw_groups)
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
        metavar=_("GROUP1,GROUP2..."),
        nargs='?',
        type=str,
        help=_("show the given groups and their subgroups"),
    )
    parser_groups.add_argument(
        'attrs',
        default=None,
        metavar=_("ATTR1,ATTR2..."),
        nargs='?',
        type=str,
        help=_("show table with the given attributes for each group "
               "(e.g. 'all', 'members', 'os', ...)"),
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
    parser_lock = subparsers.add_parser("lock", description=help_lock, help=help_lock)
    parser_lock_subparsers = parser_lock.add_subparsers()

    # bw lock add
    help_lock_add = _("Add a new lock to one or more nodes")
    parser_lock_add = parser_lock_subparsers.add_parser(
        "add",
        description=help_lock_add,
        help=help_lock_add,
    )
    parser_lock_add.set_defaults(func=bw_lock_add)
    parser_lock_add.add_argument(
        'target',
        metavar=_("NODE1,NODE2,GROUP1,bundle:BUNDLE1..."),
        type=str,
        help=_("target nodes, groups and/or bundle selectors"),
    )
    parser_lock_add.add_argument(
        "-c",
        "--comment",
        default="",
        dest='comment',
        help=_("brief description of the purpose of the lock"),
        type=str,
    )
    bw_lock_add_e_default = environ.get("BW_SOFTLOCK_EXPIRY", "8h")
    parser_lock_add.add_argument(
        "-e",
        "--expires-in",
        default=bw_lock_add_e_default,
        dest='expiry',
        help=_("how long before the lock is ignored and removed automatically "
               "(defaults to \"{}\")").format(bw_lock_add_e_default),
        type=str,
    )
    parser_lock_add.add_argument(
        "-i",
        "--items",
        default="*",
        dest='items',
        help=_("comma-separated list of item selectors the lock applies to "
               "(defaults to \"*\" meaning all)"),
        type=str,
    )
    bw_lock_add_p_default = int(environ.get("BW_NODE_WORKERS", "4"))
    parser_lock_add.add_argument(
        "-p",
        "--parallel-nodes",
        default=bw_lock_add_p_default,
        dest='node_workers',
        help=_("number of nodes to lock simultaneously "
               "(defaults to {})").format(bw_lock_add_p_default),
        type=int,
    )

    # bw lock remove
    help_lock_remove = _("Remove a lock from a node")
    parser_lock_remove = parser_lock_subparsers.add_parser(
        "remove",
        description=help_lock_remove,
        help=help_lock_remove,
    )
    parser_lock_remove.set_defaults(func=bw_lock_remove)
    parser_lock_remove.add_argument(
        'target',
        metavar=_("NODE1,NODE2,GROUP1,bundle:BUNDLE1..."),
        type=str,
        help=_("target nodes, groups and/or bundle selectors"),
    )
    parser_lock_remove.add_argument(
        'lock_id',
        metavar=_("LOCK_ID"),
        type=str,
        help=_("ID of the lock to remove (obtained with `bw lock show`)"),
    )
    bw_lock_remove_p_default = int(environ.get("BW_NODE_WORKERS", "4"))
    parser_lock_remove.add_argument(
        "-p",
        "--parallel-nodes",
        default=bw_lock_remove_p_default,
        dest='node_workers',
        help=_("number of nodes to remove lock from simultaneously "
               "(defaults to {})").format(bw_lock_remove_p_default),
        type=int,
    )

    # bw lock show
    help_lock_show = _("Show details of locks present on a node")
    parser_lock_show = parser_lock_subparsers.add_parser(
        "show",
        description=help_lock_show,
        help=help_lock_show,
    )
    parser_lock_show.set_defaults(func=bw_lock_show)
    parser_lock_show.add_argument(
        'target',
        metavar=_("NODE1,NODE2,GROUP1,bundle:BUNDLE1..."),
        type=str,
        help=_("target node"),
    )
    bw_lock_show_p_default = int(environ.get("BW_NODE_WORKERS", "4"))
    parser_lock_show.add_argument(
        "-p",
        "--parallel-nodes",
        default=bw_lock_show_p_default,
        dest='node_workers',
        help=_("number of nodes to retrieve locks from simultaneously "
               "(defaults to {})").format(bw_lock_show_p_default),
        type=int,
    )

    # bw metadata
    help_metadata = ("View a JSON representation of a node's metadata")
    parser_metadata = subparsers.add_parser(
        "metadata",
        description=help_metadata,
        help=help_metadata,
    )
    parser_metadata.set_defaults(func=bw_metadata)
    parser_metadata.add_argument(
        'target',
        metavar=_("NODE"),
        type=str,
        help=_("node to print JSON-formatted metadata for"),
    )
    parser_metadata.add_argument(
        'keys',
        default=[],
        metavar=_("KEY"),
        nargs='*',
        type=str,
        help=_("print only partial metadata from the given space-separated key path (e.g. `bw metadata mynode users jdoe` to show `mynode.metadata['users']['jdoe']`)"),
    )
    parser_metadata.add_argument(
        "--blame",
        action='store_true',
        dest='blame',
        help=_("show where each piece of metadata comes from"),
    )
    parser_metadata.add_argument(
        "-t",
        "--table",
        action='store_true',
        dest='table',
        help=_(
            "show a table of selected metadata values from multiple nodes instead; "
            "allows for multiple comma-separated paths in KEY; "
            "allows for node selectors in NODE (e.g. 'NODE1,NODE2,GROUP1,bundle:BUNDLE1...')"
        ),
    )

    # bw nodes
    help_nodes = _("List nodes in this repository")
    parser_nodes = subparsers.add_parser("nodes", description=help_nodes, help=help_nodes)
    parser_nodes.set_defaults(func=bw_nodes)
    parser_nodes.add_argument(
        "-i",
        "--inline",
        action='store_true',
        dest='inline',
        help=_("keep lists on a single line (for grep)"),
    )
    parser_nodes.add_argument(
        'target',
        default=None,
        metavar=_("NODE1,NODE2,GROUP1,bundle:BUNDLE1..."),
        nargs='?',
        type=str,
        help=_("filter according to nodes, groups and/or bundle selectors"),
    )
    parser_nodes.add_argument(
        'attrs',
        default=None,
        metavar=_("ATTR1,ATTR2..."),
        nargs='?',
        type=str,
        help=_("show table with the given attributes for each node "
               "(e.g. 'all', 'groups', 'bundles', 'hostname', 'os', ...)"),
    )

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
    help_plot_node = _("Plot items and their dependencies for the given node")
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
        help=_("do not show auto-generated dependencies and items"),
    )
    parser_plot_subparsers_node.add_argument(
        "--no-depends-conc",
        action='store_false',
        dest='depends_concurrency',
        help=_("do not show concurrency blocker dependencies"),
    )
    parser_plot_subparsers_node.add_argument(
        "--no-depends-regular",
        action='store_false',
        dest='depends_regular',
        help=_("do not show regular user-defined dependencies"),
    )
    parser_plot_subparsers_node.add_argument(
        "--no-depends-reverse",
        action='store_false',
        dest='depends_reverse',
        help=_("do not show reverse dependencies ('needed_by')"),
    )
    parser_plot_subparsers_node.add_argument(
        "--no-depends-static",
        action='store_false',
        dest='depends_static',
        help=_("do not show static dependencies"),
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

    # bw repo plugin
    parser_repo_subparsers_plugin = parser_repo_subparsers.add_parser("plugin")
    parser_repo_subparsers_plugin_subparsers = parser_repo_subparsers_plugin.add_subparsers()

    # bw repo plugin install
    parser_repo_subparsers_plugin_install = parser_repo_subparsers_plugin_subparsers.add_parser("install")
    parser_repo_subparsers_plugin_install.set_defaults(func=bw_repo_plugin_install)
    parser_repo_subparsers_plugin_install.add_argument(
        'plugin',
        metavar=_("PLUGIN_NAME"),
        type=str,
        help=_("name of plugin to install"),
    )
    parser_repo_subparsers_plugin_install.add_argument(
        "-f",
        "--force",
        action='store_true',
        dest='force',
        help=_("overwrite existing files when installing"),
    )

    # bw repo plugin list
    parser_repo_subparsers_plugin_list = parser_repo_subparsers_plugin_subparsers.add_parser("list")
    parser_repo_subparsers_plugin_list.set_defaults(func=bw_repo_plugin_list)

    # bw repo plugin remove
    parser_repo_subparsers_plugin_remove = parser_repo_subparsers_plugin_subparsers.add_parser("remove")
    parser_repo_subparsers_plugin_remove.set_defaults(func=bw_repo_plugin_remove)
    parser_repo_subparsers_plugin_remove.add_argument(
        'plugin',
        metavar=_("PLUGIN_NAME"),
        type=str,
        help=_("name of plugin to remove"),
    )
    parser_repo_subparsers_plugin_remove.add_argument(
        "-f",
        "--force",
        action='store_true',
        dest='force',
        help=_("remove files even if locally modified"),
    )

    # bw repo plugin search
    parser_repo_subparsers_plugin_search = parser_repo_subparsers_plugin_subparsers.add_parser("search")
    parser_repo_subparsers_plugin_search.set_defaults(func=bw_repo_plugin_search)
    parser_repo_subparsers_plugin_search.add_argument(
        'term',
        metavar=_("SEARCH_STRING"),
        nargs='?',
        type=str,
        help=_("look for this string in plugin names and descriptions"),
    )

    # bw repo plugin update
    parser_repo_subparsers_plugin_update = parser_repo_subparsers_plugin_subparsers.add_parser("update")
    parser_repo_subparsers_plugin_update.set_defaults(func=bw_repo_plugin_update)
    parser_repo_subparsers_plugin_update.add_argument(
        'plugin',
        default=None,
        metavar=_("PLUGIN_NAME"),
        nargs='?',
        type=str,
        help=_("name of plugin to update"),
    )
    parser_repo_subparsers_plugin_update.add_argument(
        "-c",
        "--check-only",
        action='store_true',
        dest='check_only',
        help=_("only show what would be updated"),
    )
    parser_repo_subparsers_plugin_update.add_argument(
        "-f",
        "--force",
        action='store_true',
        dest='force',
        help=_("overwrite local modifications when updating"),
    )

    # bw run
    help_run = _("Run a one-off command on a number of nodes")
    parser_run = subparsers.add_parser("run", description=help_run, help=help_run)
    parser_run.set_defaults(func=bw_run)
    parser_run.add_argument(
        'target',
        metavar=_("NODE1,NODE2,GROUP1,bundle:BUNDLE1..."),
        type=str,
        help=_("target nodes, groups and/or bundle selectors"),
    )
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
    bw_run_p_default = int(environ.get("BW_NODE_WORKERS", "1"))
    parser_run.add_argument(
        "-p",
        "--parallel-nodes",
        default=bw_run_p_default,
        dest='node_workers',
        help=_("number of nodes to run command on simultaneously "
               "(defaults to {})").format(bw_run_p_default),
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
                  "change in future releases). Currently, the default is -IJKM "
                  "if specific nodes are given and -HIJKMS if testing the "
                  "entire repo.")
    parser_test = subparsers.add_parser("test", description=help_test, help=help_test)
    parser_test.set_defaults(func=bw_test)
    parser_test.add_argument(
        'target',
        default=None,
        metavar=_("NODE1,NODE2,GROUP1,bundle:BUNDLE1..."),
        nargs='?',
        type=str,
        help=_("target nodes, groups and/or bundle selectors (defaults to all)"),
    )
    parser_test.add_argument(
        "-c",
        "--plugin-conflicts",
        action='store_true',
        dest='plugin_conflicts',
        help=_("check for local modifications to files installed by plugins"),
    )
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
        "--metadata-collisions",
        action='store_true',
        dest='metadata_collisions',
        help=_("check for conflicting metadata keys in group metadata"),
    )
    parser_test.add_argument(
        "-o",
        "--orphaned-bundles",
        action='store_true',
        dest='orphaned_bundles',
        help=_("check for bundles not assigned to any node"),
    )
    parser_test.add_argument(
        "-s",
        "--secret-rotation",
        default=None,
        dest='ignore_secret_identifiers',
        help=_("ensure every string passed to repo.vault.[human_]password_for() is used at least "
               "twice (using it only once means you're probably managing only one end of an "
               "authentication, making it dangerous to rotate your .secrets.cfg); PATTERNS is a "
               "comma-separated list of regex patterns for strings to ignore in this check "
               "(just pass an empty string if you don't need to ignore anything)"),
        metavar="PATTERNS",
        type=str,
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
    parser_verify = subparsers.add_parser("verify", description=help_verify, help=help_verify)
    parser_verify.set_defaults(func=bw_verify)
    parser_verify.add_argument(
        'target',
        metavar=_("NODE1,NODE2,GROUP1,bundle:BUNDLE1..."),
        type=str,
        help=_("target nodes, groups and/or bundle selectors"),
    )
    parser_verify.add_argument(
        "-a",
        "--show-all",
        action='store_true',
        dest='show_all',
        help=_("show correct items as well as incorrect ones"),
    )
    bw_verify_p_default = int(environ.get("BW_NODE_WORKERS", "4"))
    parser_verify.add_argument(
        "-p",
        "--parallel-nodes",
        default=bw_verify_p_default,
        dest='node_workers',
        help=_("number of nodes to verify simultaneously "
               "(defaults to {})").format(bw_verify_p_default),
        type=int,
    )
    bw_verify_p_items_default = int(environ.get("BW_ITEM_WORKERS", "4"))
    parser_verify.add_argument(
        "-P",
        "--parallel-items",
        default=bw_verify_p_items_default,
        dest='item_workers',
        help=_("number of items to verify simultaneously on each node "
               "(defaults to {})").format(bw_verify_p_items_default),
        type=int,
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
    return parser
