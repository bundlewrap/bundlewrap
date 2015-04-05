# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from getpass import getpass
import logging
from os import getcwd
import re
from sys import argv, exit, stderr, stdout

from ..exceptions import NoSuchRepository
from ..repo import Repository
from ..utils.text import force_text, mark_for_translation as _, red
from .parser import build_parser_bw

ANSI_ESCAPE = re.compile(r'\x1b[^m]*m')


class FilteringHandler(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            stream = stderr
        else:
            stream = stdout

        try:
            msg = self.format(record)

            if stream.isatty():
                stream.write(msg)
            else:
                stream.write(ANSI_ESCAPE.sub("", msg).encode('utf-8'))
            stream.write("\n")

            self.acquire()
            try:
                stream.flush()
            finally:
                self.release()
        except:
            self.handleError(record)


def set_up_logging(debug=False, interactive=False):
    if debug:
        format = "%(asctime)s [%(levelname)s:%(name)s:%(process)d] %(message)s"
        level = logging.DEBUG
    elif interactive:
        format = "%(message)s"
        level = logging.ERROR
    else:
        format = "%(message)s"
        level = logging.INFO

    formatter = logging.Formatter(format)

    handler = FilteringHandler()
    handler.setFormatter(formatter)
    handler.setLevel(level)

    root = logging.getLogger()
    root.addHandler(handler)

    logger = logging.getLogger('bundlewrap')
    logger.setLevel(level)

    logging.getLogger('paramiko').setLevel(logging.ERROR)
    logging.getLogger('passlib').setLevel(logging.ERROR)


def main(*args):
    """
    Entry point for the 'bw' command line utility.

    args:   used for integration tests
    """
    if not args:
        args = argv[1:]

    parser_bw = build_parser_bw()
    pargs = parser_bw.parse_args(args)

    try:
        interactive = pargs.interactive
    except AttributeError:
        interactive = False

    set_up_logging(
        debug=pargs.debug,
        interactive=interactive,
    )

    if len(args) >= 1 and (
        args[0] == b"--version" or
        (len(args) >= 2 and args[0] == b"repo" and args[1] == b"create") or
        args[0] == b"zen" or
        b"-h" in args or
        b"--help" in args
    ):
        # 'bw repo create' is a special case that only takes a path
        repo = getcwd()
    else:
        try:
            repo = Repository(getcwd())
        except NoSuchRepository:
            print(_("{x} The current working directory "
                    "is not a BundleWrap repository.".format(x=red("!"))))
            exit(1)

    # convert all string args into text
    text_args = {key: force_text(value) for key, value in vars(pargs).items()}

    repo.add_ssh_host_keys = pargs.add_ssh_host_keys

    output = pargs.func(repo, text_args)
    if output is None:
        output = ()

    return_code = 0

    for line in output:
        if isinstance(line, int):
            return_code = line
            break
        else:
            print(line.encode('utf-8'))

    exit(return_code)
