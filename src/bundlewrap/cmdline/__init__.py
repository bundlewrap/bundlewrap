# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from codecs import getwriter
import logging
from os import environ, getcwd
import re
from sys import argv, exit, stderr, stdout

from ..exceptions import NoSuchRepository
from ..repo import Repository
from ..utils.text import force_text, mark_for_translation as _, red
from .parser import build_parser_bw


ANSI_ESCAPE = re.compile(r'\x1b[^m]*m')

try:
    STDERR_WRITER = getwriter('utf-8')(stderr.buffer)
except AttributeError:  # Python 2
    STDERR_WRITER = getwriter('utf-8')(stderr)

try:
    STDOUT_WRITER = getwriter('utf-8')(stdout.buffer)
except AttributeError:  # Python 2
    STDOUT_WRITER = getwriter('utf-8')(stdout)


class FilteringHandler(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            stream = STDERR_WRITER
        else:
            stream = STDOUT_WRITER

        try:
            msg = self.format(record)

            if stream.isatty():
                stream.write(msg)
            else:
                stream.write(ANSI_ESCAPE.sub("", msg))
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

    text_args = [force_text(arg) for arg in args]

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

    environ.setdefault('BWADDHOSTKEYS', "1" if pargs.add_ssh_host_keys else "0")

    if len(text_args) >= 1 and (
        text_args[0] == "--version" or
        (len(text_args) >= 2 and text_args[0] == "repo" and text_args[1] == "create") or
        text_args[0] == "zen" or
        "-h" in text_args or
        "--help" in text_args
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
            return  # used during texting when exit() is mocked

    # convert all string args into text
    text_pargs = {key: force_text(value) for key, value in vars(pargs).items()}

    output = pargs.func(repo, text_pargs)
    if output is None:
        output = ()

    return_code = 0

    for line in output:
        if isinstance(line, int):
            return_code = line
            break
        else:
            STDOUT_WRITER.write(line)

    exit(return_code)
