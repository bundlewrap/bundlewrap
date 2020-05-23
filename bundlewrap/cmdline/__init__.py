from cProfile import Profile
from functools import wraps
from os import environ
from os.path import abspath
from shlex import quote
from sys import argv, exit, stderr, stdout
from traceback import format_exc, print_exc


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

    text_args = [force_text(arg) for arg in args]

    parser_bw = build_parser_bw()
    pargs = parser_bw.parse_args(args)
    if not hasattr(pargs, 'func'):
        parser_bw.print_help()
        exit(2)
    if pargs.profile:
        profile = Profile()
        profile.enable()

    path = abspath(pargs.repo_path)
    io.debug_mode = pargs.debug
    io.activate()
    io.debug(_("invocation: {}").format(" ".join([force_text(arg) for arg in argv])))

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
        try:
            repo = Repository(path)
        except NoSuchRepository:
            io.stderr(_(
                "{x} {path} "
                "is not a BundleWrap repository."
            ).format(path=quote(abspath(pargs.repo_path)), x=red("!!!")))
            io.deactivate()
            exit(1)
        except MissingRepoDependency as exc:
            io.stderr(str(exc))
            io.deactivate()
            exit(1)
        except Exception:
            io.stderr(format_exc())
            io.deactivate()
            exit(1)

    # convert all string args into text
    text_pargs = {key: force_text(value) for key, value in vars(pargs).items()}

    try:
        pargs.func(repo, text_pargs)
    finally:
        io.deactivate()
        if pargs.profile:
            profile.disable()
            profile.dump_stats(pargs.profile)
