import argparse
from os import getcwd

from . import VERSION_STRING
from .exceptions import NoSuchNode
from .repo import Repository
from .utils import mark_for_translation as _


def bw_nodes(repo, args):
    for node in repo.nodes:
        if args.show_hostnames:
            yield node.hostname
        else:
            yield node.name


def bw_run(repo, args):
    try:
        targets = [repo.get_node(args.target)]
    except NoSuchNode:
        targets = repo.get_group(args.target).nodes
    for node in targets:
        result = node.run(args.command, sudo=args.sudo)
        if result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                yield "{} (stdout): {}".format(node.name, line)
        if result.stderr.strip():
            for line in result.stderr.strip().split("\n"):
                yield "{} (stderr): {}".format(node.name, line)


def build_parser_bw():
    parser = argparse.ArgumentParser(prog="bw")
    parser.add_argument(
        "--version",
        action='version',
        version=VERSION_STRING,
    )
    subparsers = parser.add_subparsers(
        title=_("subcommands"),
        help=_("use 'bw <subcommand> --help' for more info"),
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

    # bw run
    parser_run = subparsers.add_parser("run")
    parser_run.set_defaults(func=bw_run)
    parser_run.add_argument(
        'target',
        metavar=_("NODE|GROUP"),
        type=str,
        help=_("target node or group"),
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
    return parser


def main():
    """
    Entry point for the 'bw' command line utility.
    """
    parser_bw = build_parser_bw()
    args = parser_bw.parse_args()
    repo = Repository(getcwd())
    for line in args.func(repo, args):
        print(line)
