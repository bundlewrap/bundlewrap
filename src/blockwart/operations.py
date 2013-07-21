from stat import S_IRUSR, S_IWUSR

from fabric.api import prefix
from fabric.api import put as _fabric_put
from fabric.api import run as _fabric_run
from fabric.api import sudo as _fabric_sudo
from fabric.state import env, output

from .exceptions import RemoteException
from .utils import LOG
from .utils.text import mark_for_translation as _

env.warn_only = True
# silence fabric
for key in output:
    output[key] = False


class RunResult(object):
    def __init__(self):
        self.return_code = None
        self.stderr = None
        self.stdout = None

    def __str__(self):
        return self.stdout


def run(hostname, command, ignore_failure=False, sudo=True):
    """
    Runs a command on a remote system.
    """
    env.host_string = hostname

    LOG.debug("running on {}: {}".format(
        hostname,
        command
    ))

    runner = _fabric_sudo if sudo else _fabric_run

    with prefix("export LANG=C"):
        fabric_result = runner(
            command,
            shell=True,
            pty=True,
            combine_stderr=False,
        )

    if not fabric_result.succeeded and not ignore_failure:
        raise RemoteException(_(
            "Non-zero return code running '{}' on '{}': {}").format(
                command,
                hostname,
                fabric_result
            )
        )

    result = RunResult()
    result.stdout = str(fabric_result)
    result.stderr = fabric_result.stderr
    result.return_code = fabric_result.return_code
    return result


def upload(hostname, local_path, remote_path, ignore_failure=False):
    """
    Upload a file.
    """
    LOG.debug(_("uploading to {}: {} -> {}").format(
        hostname, local_path, remote_path))
    env.host_string = hostname
    fabric_result = _fabric_put(
        local_path=local_path,
        remote_path=remote_path,
        use_sudo=True,
        mirror_local_mode=False,
        mode=S_IRUSR | S_IWUSR,
    )
    if not ignore_failure and fabric_result.failed:
        raise RemoteException(_(
            "upload to {} failed for: {}").format(
                hostname,
                ", ".join(fabric_result.failed),
            )
        )
