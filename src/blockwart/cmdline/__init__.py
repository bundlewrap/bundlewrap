import logging
from os import getcwd
from sys import argv, exit, stdout

from fabric.network import disconnect_all

from ..exceptions import NoSuchRepository
from ..repo import Repository
from ..utils.text import mark_for_translation as _, red
from .parser import build_parser_bw


def set_up_logging(debug=False, interactive=False):
    if debug:
        format = "%(asctime)s [%(levelname)s:%(name)s:%(process)d] %(message)s"
        level = logging.DEBUG
    elif interactive:
        format = "%(message)s"
        level = logging.ERROR
    else:
        format = "%(message)s"
        level = logging.WARNING

    handler = logging.StreamHandler(stdout)
    handler.setLevel(level)
    formatter = logging.Formatter(format)
    handler.setFormatter(formatter)
    logger = logging.getLogger('blockwart')
    logger.addHandler(handler)
    logger.setLevel(level)

    if not debug:
        logging.getLogger('paramiko').setLevel(logging.ERROR)


def main(*args):
    """
    Entry point for the 'bw' command line utility.

    args:   used for integration tests
    """
    if not args:
        args = argv[1:]

    if len(args) >= 1 and args[0] == "repo":
        # don't try to validate existing repo with 'bw repo create' etc.
        repo = Repository(getcwd(), skip_validation=True)
    else:
        try:
            repo = Repository(getcwd(), skip_validation=False)
        except NoSuchRepository:
            print(_("{} The current working directory "
                    "is not a Blockwart repository.".format(red("!"))))
            exit(1)

    parser_bw = build_parser_bw()
    args = parser_bw.parse_args(args)

    try:
        interactive = args.interactive
    except AttributeError:
        interactive = False

    set_up_logging(
        debug=args.debug,
        interactive=interactive,
    )

    output = args.func(repo, args)
    if output is None:
        output = ()

    for line in output:
        print(line.encode('utf-8'))

    # clean up Fabric connections
    disconnect_all()
