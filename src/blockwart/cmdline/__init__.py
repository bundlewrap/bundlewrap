import logging
from os import getcwd
from sys import argv, stdout

from ..repo import Repository
from .parser import build_parser_bw


def set_up_logging(debug=False, verbose=False):
    if debug:
        format = "%(asctime)s [%(levelname)s:%(name)s:%(process)d] %(message)s"
        level = logging.DEBUG
    elif verbose:
        format = "%(message)s"
        level = logging.INFO
    else:
        format = "%(message)s"
        level = logging.WARNING

    handler = logging.StreamHandler(stdout)
    handler.setLevel(level)
    formatter = logging.Formatter(format)
    handler.setFormatter(formatter)

    if debug:
        # add handler to root logger so we can show messages from paramiko
        logger = logging.getLogger()
    else:
        logger = logging.getLogger('blockwart')
    logger.addHandler(handler)
    logger.setLevel(level)


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

    set_up_logging(debug=args.debug, verbose=args.verbose)

    args.func(repo, args)
