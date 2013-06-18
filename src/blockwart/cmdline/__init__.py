from os import getcwd

from ..repo import Repository
from .parser import build_parser_bw


def main():
    """
    Entry point for the 'bw' command line utility.
    """
    parser_bw = build_parser_bw()
    args = parser_bw.parse_args()
    repo = Repository(getcwd())
    for line in args.func(repo, args):
        print(line)
