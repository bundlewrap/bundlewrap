import argparse

from . import VERSION_STRING
from .utils import mark_for_translation as _


def build_parser_bw():
    parser = argparse.ArgumentParser(prog="bw")
    subparsers = parser.add_subparsers(
        title=_("subcommands"),
        help=_("use 'bw <subcommand> --help' for more info"),
    )
    parser.add_argument(
        "--version",
        action='version',
        version=VERSION_STRING,
    )
    return parser


def main():
    """
    Entry point for the 'bw' command line utility.
    """
    parser_bw = build_parser_bw()
    args = parser_bw.parse_args()
    args.func()
