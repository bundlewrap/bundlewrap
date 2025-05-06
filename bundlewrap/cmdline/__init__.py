# PYTHON_ARGCOMPLETE_OK

from cProfile import Profile
from os import environ
from os.path import abspath
from shlex import quote
from sys import argv, exit
from traceback import format_exc


from ..exceptions import NoSuchRepository, MissingRepoDependency
from ..repo import Repository
from ..utils.cmdline import suppress_broken_pipe_msg
from ..utils.text import force_text, mark_for_translation as _, red
from ..utils.ui import io
from .parser import build_parser_bw


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
