from argparse import ArgumentParser

from .. import VERSION_STRING
from ..utils.text import mark_for_translation as _
from .apply import bw_apply
from .groups import bw_groups
from .items import bw_items
from .nodes import bw_nodes
from .repo import bw_repo_bundle_create, bw_repo_create, bw_repo_debug, bw_repo_plot
from .run import bw_run
from .verify import bw_verify


def build_parser_bw():
    parser = ArgumentParser(prog="bw", description=_(
        "Blockwart - config management for Python addicts"
    ))
    parser.add_argument(
        '-d',
        '--debug',
        action='store_true',
        default=False,
        dest='debug',
        help=_("print debugging info (implies -v)"),
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
    parser_apply = subparsers.add_parser("apply")
    parser_apply.set_defaults(func=bw_apply)
    parser_apply.add_argument(
        'target',
        metavar=_("NODE1,NODE2,GROUP1,bundle:BUNDLE1..."),
        type=str,
        help=_("target nodes, groups and/or bundle selectors"),
    )
    parser_apply.add_argument(
        '-i',
        '--interactive',
        action='store_true',
        default=False,
        dest='interactive',
        help=_("ask before applying each item"),
    )
    parser_apply.add_argument(
        '-p',
        '--parallel-nodes',
        default=4,
        dest='node_workers',
        help=_("number of nodes to apply to simultaneously"),
        type=int,
    )
    parser_apply.add_argument(
        '-P',
        '--parallel-items',
        default=4,
        dest='item_workers',
        help=_("number of items to apply to simultaneously on each node"),
        type=int,
    )

    # bw groups
    parser_groups = subparsers.add_parser("groups")
    parser_groups.set_defaults(func=bw_groups)
    parser_groups.add_argument(
        '-n',
        '--nodes',
        action='store_true',
        dest='show_nodes',
        help=_("show nodes for each group"),
    )

    # bw items
    parser_items = subparsers.add_parser("items")
    parser_items.set_defaults(func=bw_items)
    parser_items.add_argument(
        'node',
        metavar=_("NODE"),
        type=str,
        help=_("list items for this node"),
    )
    parser_items.add_argument(
        '-w',
        '--write-file-previews',
        default=None,
        dest='file_preview_path',
        metavar=_("DIRECTORY"),
        required=False,
        type=str,
        help=_("create DIRECTORY and fill it with rendered file previews"),
    )
    parser_items.add_argument(
        '--repr',
        action='store_true',
        dest='show_repr',
        help=_("show more verbose representation of each item"),
    )

    # bw nodes
    parser_nodes = subparsers.add_parser("nodes")
    parser_nodes.set_defaults(func=bw_nodes)
    parser_nodes.add_argument(
        '--hostnames',
        action='store_true',
        dest='show_hostnames',
        help=_("show hostnames instead of node names"),
    )
    parser_nodes.add_argument(
        '-g',
        '--filter-group',
        default=None,
        dest='filter_group',
        metavar=_("GROUP"),
        required=False,
        type=str,
        help=_("show only nodes in the given group"),
    )
    parser_nodes.add_argument(
        '--groups',
        action='store_true',
        dest='show_groups',
        help=_("show group membership for each node"),
    )

    # bw repo
    parser_repo = subparsers.add_parser("repo")
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

    # bw repo debug
    parser_repo_subparsers_debug = parser_repo_subparsers.add_parser("debug")
    parser_repo_subparsers_debug.set_defaults(func=bw_repo_debug)
    parser_repo_subparsers_debug.add_argument(
        '-n',
        '--node',
        default=None,
        dest='node',
        metavar=_("NODE"),
        required=False,
        type=str,
        help=_("name of node to inspect"),
    )

    # bw repo plot
    parser_repo_subparsers_plot = parser_repo_subparsers.add_parser("plot")
    parser_repo_subparsers_plot.set_defaults(func=bw_repo_plot)
    parser_repo_subparsers_plot.add_argument(
        'node',
        metavar=_("NODE"),
        type=str,
        help=_("node to plot"),
    )
    parser_repo_subparsers_plot.add_argument(
        '--no-depends-auto',
        action='store_false',
        dest='depends_auto',
        help=_("do not show auto-generated dependencies and items"),
    )
    parser_repo_subparsers_plot.add_argument(
        '--no-depends-regular',
        action='store_false',
        dest='depends_regular',
        help=_("do not show regular user-defined dependencies"),
    )
    parser_repo_subparsers_plot.add_argument(
        '--no-depends-static',
        action='store_false',
        dest='depends_static',
        help=_("do not show static dependencies"),
    )

    # bw run
    parser_run = subparsers.add_parser("run")
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
        '--no-sudo',
        action='store_false',
        dest='sudo',
        help=_("do not use sudo, execute with user privs"),
    )
    parser_run.add_argument(
        '-f',
        '--may-fail',
        action='store_true',
        dest='may_fail',
        help=_("ignore non-zero exit codes"),
    )
    parser_run.add_argument(
        '-p',
        '--parallel-nodes',
        default=1,
        dest='node_workers',
        help=_("number of nodes to run command on simultaneously"),
        type=int,
    )

    # bw verify
    parser_verify = subparsers.add_parser("verify")
    parser_verify.set_defaults(func=bw_verify)
    parser_verify.add_argument(
        'target',
        metavar=_("NODE1,NODE2,GROUP1,bundle:BUNDLE1..."),
        type=str,
        help=_("target nodes, groups and/or bundle selectors"),
    )
    parser_verify.add_argument(
        '-p',
        '--parallel-nodes',
        default=4,
        dest='node_workers',
        help=_("number of nodes to verify to simultaneously"),
        type=int,
    )
    parser_verify.add_argument(
        '-P',
        '--parallel-items',
        default=4,
        dest='item_workers',
        help=_("number of items to verify to simultaneously on each node"),
        type=int,
    )

    return parser
