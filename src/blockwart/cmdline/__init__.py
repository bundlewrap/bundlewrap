from os import getcwd
from sys import argv

from ..repo import Repository
from .parser import build_parser_bw


def main(*args):
    """
    Entry point for the 'bw' command line utility.

    args:   used for integration tests
    """
    if not args:
        args = argv[1:]

    if len(args) >= 1 and args[0] == "repo":
        repo = Repository(getcwd(), skip_validation=True)
    else:
        repo = Repository(getcwd(), skip_validation=False)

    parser_bw = build_parser_bw()
    args = parser_bw.parse_args(args)

    for line in args.func(repo, args):
        print(line)
