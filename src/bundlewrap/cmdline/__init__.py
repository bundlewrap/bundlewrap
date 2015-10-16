# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os import environ, getcwd
from sys import argv, exit

from ..exceptions import NoSuchRepository
from ..repo import Repository
from ..utils.text import force_text, mark_for_translation as _, red
from ..utils.ui import io
from .parser import build_parser_bw


def main(*args, **kwargs):
    """
    Entry point for the 'bw' command line utility.

    The args and path parameters are used for integration tests.
    """
    if not args:
        args = argv[1:]
    path = kwargs.get('path', getcwd())

    text_args = [force_text(arg) for arg in args]

    parser_bw = build_parser_bw()
    pargs = parser_bw.parse_args(args)

    io.activate_as_parent(debug=pargs.debug)

    environ.setdefault('BWADDHOSTKEYS', "1" if pargs.add_ssh_host_keys else "0")

    if len(text_args) >= 1 and (
        text_args[0] == "--version" or
        (len(text_args) >= 2 and text_args[0] == "repo" and text_args[1] == "create") or
        text_args[0] == "zen" or
        "-h" in text_args or
        "--help" in text_args
    ):
        # 'bw repo create' is a special case that only takes a path
        repo = path
    else:
        try:
            repo = Repository(path)
        except NoSuchRepository:
            io.stderr(_(
                "{x} The current working directory "
                "is not a BundleWrap repository.\n".format(x=red("!"))
            ))
            exit(1)
            return  # used during texting when exit() is mocked

    # convert all string args into text
    text_pargs = {key: force_text(value) for key, value in vars(pargs).items()}

    try:
        output = pargs.func(repo, text_pargs)
        if output is None:
            output = ()

        return_code = 0

        for line in output:
            if isinstance(line, int):
                return_code = line
                break
            else:
                io.stdout(line)
    finally:
        io.shutdown()

    if return_code != 0:  # not raising SystemExit every time to ease testing
        exit(return_code)
