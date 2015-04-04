# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

from base64 import b64decode
from pipes import quote
from select import select
from subprocess import Popen
from threading import Event, Thread
from os import close, pipe, read

from .exceptions import RemoteException
from .utils import LOG
from .utils.text import force_text, mark_for_translation as _, randstr
from .utils.ui import LineBuffer


def output_thread_body(line_buffer, read_fd, quit_event):
    while not quit_event.is_set():
        r, w, x = select([read_fd], [], [], 0.1)
        if r:
            line_buffer.write(read(read_fd, 1024))


def download(hostname, remote_path, local_path, ignore_failure=False, password=None):
    """
    Download a file.
    """
    # See issue #39.

    LOG.debug(_("downloading {host}:{path} -> {target}").format(
        host=hostname, path=remote_path, target=local_path))

    if XXX_SUCCESS:
        with open(local_path, "w") as f:
            f.write()
    elif not ignore_failure:
        raise RemoteException(_(
            "reading file '{path}' on {host} failed: {error}").format(
                error=None,
                host=hostname,
                path=remote_path,
            )
        )


class RunResult(object):
    def __init__(self):
        self.return_code = None
        self.stderr = None
        self.stdout = None

    def __str__(self):
        return self.stdout


def run(hostname, command, ignore_failure=False, log_function=None):
    """
    Runs a command on a remote system.
    """
    stderr_lb = LineBuffer(log_function)
    stdout_lb = LineBuffer(log_function)

    LOG.debug("running on {host}: {command}".format(command=command, host=hostname))

    stdout_fd_r, stdout_fd_w = pipe()
    stderr_fd_r, stderr_fd_w = pipe()

    ssh_process = Popen(
        ["ssh", hostname, "LANG=C sudo bash -c " + quote(command)],
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

    LOG.debug("command finished with return code {}".format(ssh_process.returncode))

    result = RunResult()
    result.stdout = stdout_lb.record.getvalue()
    result.stderr = stderr_lb.record.getvalue()
    result.return_code = ssh_process.returncode

    if not result.return_code == 0 and not ignore_failure:
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
           group="", ignore_failure=False, password=None):
    """
    Upload a file.
    """
    LOG.debug(_("uploading {path} -> {host}:{target}").format(
        host=hostname, path=local_path, target=remote_path))
    temp_filename = ".bundlewrap_tmp_" + randstr()

    if not ignore_failure and not XXX_SUCCESS:
        raise RemoteException(_(
            "upload to {host} failed for: {failed}").format(
                failed=", ".join(),
                host=hostname,
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
            password=password,
        )

    if mode:
        run(
            hostname,
            "chmod {} {}".format(
                mode,
                quote(temp_filename),
            ),
            password=password,
        )

    run(
        hostname,
        "mv -f {} {}".format(
            quote(temp_filename),
            quote(remote_path),
        ),
        password=password,
    )
