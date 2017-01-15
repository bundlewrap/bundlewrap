from subprocess import Popen, PIPE
from os import setpgrp
from pipes import quote

from . import RunResult
from ..exceptions import RemoteException
from ..utils.text import force_text, mark_for_translation as _, randstr
from ..utils.ui import io


def download(
    container_id,
    remote_path,
    local_path,
):
    """
    Download a file.
    """
    io.debug(_("downloading {host}:{path} -> {target}").format(
        host=container_id, path=remote_path, target=local_path))

    docker_process = Popen(
        [
            "docker", "cp",
            "{}:{}".format(container_id, remote_path),
            local_path,
        ],
        preexec_fn=setpgrp,
    )
    docker_process.communicate()
    assert docker_process.returncode == 0


def run(
    container_id,
    command,
    ignore_failure=False,
    wrapper_inner="{}",
    wrapper_outer="{}",
):
    cmd_id = randstr(length=4).upper()
    docker_command = [
        "docker", "exec", "--privileged",
        container_id,
        wrapper_outer.format(quote(wrapper_inner.format(command))),
    ]
    io.debug("running command with ID {}: {}".format(cmd_id, " ".join(docker_command)))

    docker_process = Popen(
        docker_command,
        preexec_fn=setpgrp,
        stdin=PIPE,
        stderr=PIPE,
        stdout=PIPE,
    )
    docker_process.communicate()

    io.debug("command with ID {} finished with return code {}".format(
        cmd_id,
        docker_process.returncode,
    ))

    result = RunResult()
    result.stderr = docker_process.stderr
    result.stdout = docker_process.stdout
    result.return_code = docker_process.returncode

    if result.return_code != 0:
        error_msg = _(
            "Non-zero return code ({rcode}) running '{command}' "
            "with ID {id} on '{host}':\n\n{result}\n\n"
        ).format(
            command=command,
            host=container_id,
            id=cmd_id,
            rcode=result.return_code,
            result=force_text(result.stdout) + force_text(result.stderr),
        )
        io.debug(error_msg)
        if not ignore_failure:
            raise RemoteException(error_msg)

    return result


def upload(
    container_id,
    local_path,
    remote_path,
):
    """
    Upload a file.
    """
    io.debug(_("uploading {path} -> {host}:{target}").format(
        host=container_id, path=local_path, target=remote_path))

    docker_process = Popen(
        [
            "docker", "cp",
            local_path,
            "{}:{}".format(container_id, remote_path),
        ],
        preexec_fn=setpgrp,
    )
    docker_process.communicate()
    assert docker_process.returncode == 0
