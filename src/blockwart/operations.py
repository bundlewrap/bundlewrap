from stat import S_IRUSR, S_IWUSR

from fabric.api import prefix
from fabric.api import get as _fabric_get
from fabric.api import put as _fabric_put
from fabric.api import run as _fabric_run
from fabric.api import sudo as _fabric_sudo
from fabric.state import env, output

from .exceptions import RemoteException
from .utils import LOG
from .utils.text import mark_for_translation as _
from .utils.ui import LineBuffer

env.use_ssh_config = True
env.warn_only = True
# silence fabric
for key in output:
    output[key] = False


class FabricUnsilencer(object):
    def __enter__(self):
        output['stderr'] = True
        output['stdout'] = True

    def __exit__(self, type, value, traceback):
        output['stderr'] = False
        output['stdout'] = False


def download(hostname, remote_path, local_path, ignore_failure=False):
    """
    Download a file.
    """
    LOG.debug(_("downloading {}:{} -> {}").format(
        hostname, remote_path, local_path))
    env.host_string = hostname
    fabric_result = _fabric_get(
        remote_path=remote_path,
        local_path=local_path,
    )
    if not ignore_failure and fabric_result.failed:
        raise RemoteException(_(
            "download from {} failed for: {}").format(
                hostname,
                ", ".join(fabric_result.failed),
            )
        )


class RunResult(object):
    def __init__(self):
        self.return_code = None
        self.stderr = None
        self.stdout = None

    def __str__(self):
        return self.stdout


def run(hostname, command, ignore_failure=False, stderr=None,
        stdout=None, pty=False, sudo=True):
    """
    Runs a command on a remote system.
    """
    env.host_string = hostname

    if stderr is None:
        stderr = LineBuffer(lambda s: None)
    if stdout is None:
        stdout = LineBuffer(lambda s: None)

    LOG.debug("running on {}: {}".format(
        hostname,
        command
    ))

    runner = _fabric_sudo if sudo else _fabric_run

    with FabricUnsilencer():
        with prefix("export LANG=C"):
            fabric_result = runner(
                command,
                shell=True,
                pty=pty,
                combine_stderr=False,
                stdout=stdout,
                stderr=stderr,
            )

    LOG.debug("command finished with return code {}".format(fabric_result.return_code))

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
    LOG.debug(_("uploading {} -> {}:{}").format(
        local_path, hostname, remote_path))
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
