# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from functools import wraps
from os import environ, getcwd
from os.path import dirname
from sys import argv, exit, stderr, stdout
from traceback import print_exc


from ..exceptions import NoSuchRepository, MissingRepoDependency
from ..repo import Repository
from ..utils.text import force_text, mark_for_translation as _, red
from ..utils.ui import io
from .parser import build_parser_bw


def suppress_broken_pipe_msg(f):
    """
    Oh boy.

    CPython does funny things with SIGPIPE. By default, it is caught and
    raised as a BrokenPipeError. When do we get a SIGPIPE? Most commonly
    when piping into head:

        bw nodes | head -n 1

    head will exit after receiving the first line, causing the kernel to
    send SIGPIPE to our process. Since in most cases, we can't just quit
    early, we simply ignore BrokenPipeError in utils.ui.write_to_stream.

    Unfortunately, Python will still print a message:

        Exception ignored in: <_io.TextIOWrapper name='<stdout>'
                               mode='w' encoding='UTF-8'>
        BrokenPipeError: [Errno 32] Broken pipe

    See also http://bugs.python.org/issue11380. The crazy try/finally
    construct below is taken from there and I quote:

        This will:
         - capture any exceptions *you've* raised as the context for the
           errors raised in this handler
         - expose any exceptions generated during this thing itself
         - prevent the interpreter dying during shutdown in
           flush_std_files by closing the files (you can't easily wipe
           out the pending writes that have failed)

    CAVEAT: There is a seamingly easier method floating around on the
    net (http://stackoverflow.com/a/16865106) that restores the default
    behavior for SIGPIPE (i.e. not turning it into a BrokenPipeError):

        from signal import signal, SIGPIPE, SIG_DFL
        signal(SIGPIPE,SIG_DFL)

    This worked fine for a while but broke when using
    multiprocessing.Manager() to share the list of jobs in utils.ui
    between processes. When the main process terminated, it quit with
    return code 141 (indicating a broken pipe), and the background
    process used for the manager continued to hang around indefinitely.
    Bonus fun: This was observed only on Ubuntu Trusty (14.04).
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except SystemExit:
            raise
        except:
            print_exc()
            exit(1)
        finally:
            try:
                stdout.flush()
            finally:
                try:
                    stdout.close()
                finally:
                    try:
                        stderr.flush()
                    finally:
                        stderr.close()
    return wrapper


@suppress_broken_pipe_msg
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
    if not hasattr(pargs, 'func'):
        parser_bw.print_help()
        exit(2)

    io.debug_mode = pargs.debug
    io.activate()

    if 'BWADDHOSTKEYS' in environ:  # TODO remove in 3.0.0
        environ.setdefault('BW_ADD_HOST_KEYS', environ['BWADDHOSTKEYS'])
    if 'BWCOLORS' in environ:  # TODO remove in 3.0.0
        environ.setdefault('BW_COLORS', environ['BWCOLORS'])
    if 'BWITEMWORKERS' in environ:  # TODO remove in 3.0.0
        environ.setdefault('BW_ITEM_WORKERS', environ['BWITEMWORKERS'])
    if 'BWNODEWORKERS' in environ:  # TODO remove in 3.0.0
        environ.setdefault('BW_NODE_WORKERS', environ['BWNODEWORKERS'])

    environ.setdefault('BW_ADD_HOST_KEYS', "1" if pargs.add_ssh_host_keys else "0")

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
        while True:
            try:
                repo = Repository(path)
                break
            except NoSuchRepository:
                if path == dirname(path):
                    io.stderr(_(
                        "{x} The current working directory "
                        "is not a BundleWrap repository."
                    ).format(x=red("!")))
                    exit(1)
                else:
                    path = dirname(path)
            except MissingRepoDependency as exc:
                io.stderr(str(exc))
                exit(1)

    # convert all string args into text
    text_pargs = {key: force_text(value) for key, value in vars(pargs).items()}

    pargs.func(repo, text_pargs)
