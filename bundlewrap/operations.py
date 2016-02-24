# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote
from select import select
from subprocess import Popen, PIPE
from threading import Event, Thread
from os import close, pipe, read

from .exceptions import RemoteException
from .utils import cached_property
from .utils.text import force_text, LineBuffer, mark_for_translation as _, randstr
from .utils.ui import io


def output_thread_body(line_buffer, read_fd, quit_event):
    while True:
        r, w, x = select([read_fd], [], [], 0.1)
        if r:
            line_buffer.write(read(read_fd, 1024))
        elif quit_event.is_set():
            return


def download(hostname, remote_path, local_path, add_host_keys=False):
    """
    Download a file.
    """
    io.debug(_("downloading {host}:{path} -> {target}").format(
        host=hostname, path=remote_path, target=local_path))

    result = run(
        hostname,
        "cat {}".format(quote(remote_path)),  # See issue #39.
        add_host_keys=add_host_keys,
    )

    if result.return_code == 0:
        with open(local_path, "wb") as f:
            f.write(result.stdout)
    else:
        raise RemoteException(_(
            "reading file '{path}' on {host} failed: {error}").format(
                error=force_text(result.stderr) + force_text(result.stdout),
                host=hostname,
                path=remote_path,
            )
        )


class RunResult(object):
    def __init__(self):
        self.return_code = None
        self.stderr = None
        self.stdout = None

    @cached_property
    def stderr_text(self):
        return force_text(self.stderr)

    @cached_property
    def stdout_text(self):
        return force_text(self.stdout)


def run(hostname, command, ignore_failure=False, add_host_keys=False, log_function=None):
    """
    Runs a command on a remote system.
    """
    stderr_lb = LineBuffer(log_function)
    stdout_lb = LineBuffer(log_function)

    io.debug("running on {host}: {command}".format(command=command, host=hostname))

    stdout_fd_r, stdout_fd_w = pipe()
    stderr_fd_r, stderr_fd_w = pipe()

    ssh_process = Popen(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no" if add_host_keys else "StrictHostKeyChecking=yes",
            hostname,
            "LANG=C sudo bash -c " + quote(command),
        ],
        stdin=PIPE,
        stderr=stderr_fd_w,
        stdout=stdout_fd_w,
    )
    quit_event = Event()
    stdout_thread = Thread(
        args=(stdout_lb, stdout_fd_r, quit_event),
        target=output_thread_body,
    )
    stderr_thread = Thread(
        args=(stderr_lb, stderr_fd_r, quit_event),
        target=output_thread_body,
    )
    stdout_thread.start()
    stderr_thread.start()
    try:
        ssh_process.communicate()
    finally:
        quit_event.set()
        stdout_thread.join()
        stderr_thread.join()
        stdout_lb.close()
        stderr_lb.close()
        for fd in (stdout_fd_r, stdout_fd_w, stderr_fd_r, stderr_fd_w):
            close(fd)

    io.debug("command finished with return code {}".format(ssh_process.returncode))

    result = RunResult()
    result.stdout = stdout_lb.record.getvalue()
    result.stderr = stderr_lb.record.getvalue()
    result.return_code = ssh_process.returncode

    if result.return_code != 0 and (not ignore_failure or result.return_code == 255):
        raise RemoteException(_(
            "Non-zero return code ({rcode}) running '{command}' on '{host}':\n\n{result}"
        ).format(
            command=command,
            host=hostname,
            rcode=result.return_code,
            result=force_text(result.stdout) + force_text(result.stderr),
        ))
    return result


def upload(hostname, local_path, remote_path, mode=None, owner="",
           group="", add_host_keys=False):
    """
    Upload a file.
    """
    io.debug(_("uploading {path} -> {host}:{target}").format(
        host=hostname, path=local_path, target=remote_path))
    temp_filename = ".bundlewrap_tmp_" + randstr()

    scp_process = Popen(
        [
            "scp",
            "-o",
            "StrictHostKeyChecking=no" if add_host_keys else "StrictHostKeyChecking=yes",
            local_path,
            "{}:{}".format(hostname, temp_filename),
        ],
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
    )
    stdout, stderr = scp_process.communicate()

    if scp_process.returncode != 0:
        raise RemoteException(_(
            "Upload to {host} failed for {failed}:\n\n{result}").format(
                failed=remote_path,
                host=hostname,
                result=force_text(stdout) + force_text(stderr),
            )
        )

    if owner or group:
        if group:
            group = ":" + quote(group)
        run(
            hostname,
            "chown {}{} {}".format(
                quote(owner),
                group,
                quote(temp_filename),
            ),
            add_host_keys=add_host_keys,
        )

    if mode:
        run(
            hostname,
            "chmod {} {}".format(
                mode,
                quote(temp_filename),
            ),
            add_host_keys=add_host_keys,
        )

    run(
        hostname,
        "mv -f {} {}".format(
            quote(temp_filename),
            quote(remote_path),
        ),
        add_host_keys=add_host_keys,
    )
