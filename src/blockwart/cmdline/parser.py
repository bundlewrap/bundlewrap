from argparse import ArgumentParser

from .. import VERSION_STRING
from ..utils.text import mark_for_translation as _
from .apply import bw_apply
from .nodes import bw_nodes
from .repo import bw_repo_create, bw_repo_debug
from .run import bw_run


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
        '-v',
        '--verbose',
        action='store_true',
        default=False,
        dest='verbose',
        help=_("more verbose output"),
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
        metavar=_("NODE1,NODE2,GROUP1,..."),
        type=str,
        help=_("target nodes and/or groups"),
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

    # bw nodes
    parser_nodes = subparsers.add_parser("nodes")
    parser_nodes.set_defaults(func=bw_nodes)
    parser_nodes.add_argument(
        '--hostnames',
        action='store_true',
        dest='show_hostnames',
        help=_("show hostnames instead of node names"),
    )

    # bw repo
    parser_repo = subparsers.add_parser("repo")
    parser_repo_subparsers = parser_repo.add_subparsers()
    parser_repo_subparsers_create = parser_repo_subparsers.add_parser("create")
    parser_repo_subparsers_create.set_defaults(func=bw_repo_create)
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

    # bw run
    parser_run = subparsers.add_parser("run")
    parser_run.set_defaults(func=bw_run)
    parser_run.add_argument(
        'target',
        metavar=_("NODE1,NODE2,GROUP1,..."),
        type=str,
        help=_("target nodes and/or groups"),
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
    return parser
