from contextlib import suppress
from datetime import datetime
from shlex import quote
from select import select
from shlex import split
from subprocess import Popen
from sys import version_info
from threading import Lock
from os import close, environ, pipe, read, setpgrp, write

from .exceptions import RemoteException
from .utils import cached_property
from .utils.text import force_text, LineBuffer, mark_for_translation as _, randstr
from .utils.ui import io

from librouteros import connect


ROUTEROS_CONNECTIONS = {}
ROUTEROS_CONNECTIONS_LOCK = Lock()


def download(
    hostname,
    remote_path,
    local_path,
    add_host_keys=False,
    username=None,
    wrapper_inner="{}",
    wrapper_outer="{}",
):
    """
    Download a file.
    """
    io.debug(_("downloading {host}:{path} -> {target}").format(
        host=hostname, path=remote_path, target=local_path))

    result = run(
        hostname,
        "cat {}".format(quote(remote_path)),  # See issue #39.
        add_host_keys=add_host_keys,
        username=username,
        wrapper_inner=wrapper_inner,
        wrapper_outer=wrapper_outer,
    )

    if result.return_code == 0:
        with open(local_path, "wb") as f:
            f.write(result.stdout)
    else:
        raise RemoteException(_(
            "reading file '{path}' on {host} failed: {error}"
        ).format(
            error=force_text(result.stderr) + force_text(result.stdout),
            host=hostname,
            path=remote_path,
        ))


class RunResult:
    def __init__(self):
        self.duration = None
        self.return_code = None
        self.stderr = None
        self.stdout = None

    @cached_property
    def stderr_text(self):
        return force_text(self.stderr)

    @cached_property
    def stdout_text(self):
        return force_text(self.stdout)


def run_local(
    command,
    data_stdin=None,
    log_function=None,
    shell=False,
):
    """
    Runs a command on the local system.
    """
    # LineBuffer objects take care of always printing complete lines
    # which have been properly terminated by a newline. This is only
    # relevant when using `bw run`.
    # Does nothing when log_function is None.
    stderr_lb = LineBuffer(log_function)
    stdout_lb = LineBuffer(log_function)

    # Create pipes which will be used by the SSH child process. We do
    # not use subprocess.PIPE because we need to be able to continuously
    # check those pipes for new output, so we can feed it to the
    # LineBuffers during `bw run`. We can't use .communicate().
    stderr_fd_r, stderr_fd_w = pipe()
    stdout_fd_r, stdout_fd_w = pipe()
    watch_readable = [stdout_fd_r, stderr_fd_r]
    close_after_fork = [stdout_fd_w, stderr_fd_w]

    # It's important that SSH never gets connected to the terminal, even
    # if we do not send data to the child. Otherwise, SSH can steal user
    # input.
    stdin_fd_r, stdin_fd_w = pipe()
    if data_stdin is None:
        data_stdin = b''
        watch_writable = []
        close_after_fork += [stdin_fd_r, stdin_fd_w]
    else:
        watch_writable = [stdin_fd_w]
        close_after_fork += [stdin_fd_r]

    cmd_id = randstr(length=4).upper()
    io.debug("running command with ID {}: {}".format(cmd_id, " ".join(command)))
    start = datetime.utcnow()

    # A word on process groups: We create a new process group that all
    # child processes live in. The point is to avoid SIGINT signals to
    # reach our children: When a user presses ^C in their terminal, the
    # signal will be sent to the foreground process group only.
    #
    # Our concept of "soft shutdown" hinges on this behavior. If we
    # didn't create a new process group, child processes would die
    # instantly.
    #
    # Older versions of Python only allow you to do this by setting
    # preexec_fn=. Using this mechanism has a huge impact on performance
    # (we did not investigate this further). As of Python 3.11, we can
    # use process_group=, which has no such impact.
    if version_info < (3, 11):
        child_process = Popen(
            command,
            preexec_fn=setpgrp,
            shell=shell,
            stdin=stdin_fd_r,
            stderr=stderr_fd_w,
            stdout=stdout_fd_w,
        )
    else:
        child_process = Popen(
            command,
            process_group=0,
            shell=shell,
            stdin=stdin_fd_r,
            stderr=stderr_fd_w,
            stdout=stdout_fd_w,
        )

    io._child_pids.append(child_process.pid)

    for fd in close_after_fork:
        close(fd)

    try:
        while len(watch_readable) + len(watch_writable) > 0:
            r, w, _ = select(watch_readable, watch_writable, [])

            for fd, lb in [(stderr_fd_r, stderr_lb), (stdout_fd_r, stdout_lb)]:
                if fd in r:
                    chunk = read(fd, 8192)
                    if chunk:
                        lb.write(chunk)
                    else:
                        close(fd)
                        watch_readable.remove(fd)

            if stdin_fd_w in w:
                if len(data_stdin) > 0:
                    written = write(stdin_fd_w, data_stdin)
                    data_stdin = data_stdin[written:]
                else:
                    close(stdin_fd_w)
                    watch_writable.remove(stdin_fd_w)

            # Why child_process.poll()? A user could use SSH
            # multiplexing with auto-forking (e.g., "ControlPersist
            # 10m"). In this case, OpenSSH forks another process which
            # holds the "master" connection. This forked process
            # *inherits* our pipes (at least stderr). Thus, only when
            # that master process finally terminates (possibly after
            # many minutes), we will be informed about EOF on our stderr
            # pipe. That doesn't work, bw will hang.
            #
            # If the child has exited, we close our end of the stderr
            # pipe. This loop will continue to read data from stdout
            # until EOF has been reached.
            if child_process.poll() is not None and stderr_fd_r in watch_readable:
                close(stderr_fd_r)
                watch_readable.remove(stderr_fd_r)
    finally:
        io._child_pids.remove(child_process.pid)

        stderr_lb.close()
        stdout_lb.close()

        # In case we get an exception, make sure to close all
        # descriptors that are still open.
        for fd in watch_readable + watch_writable:
            close(fd)

        child_process.wait()

    io.debug("command with ID {} finished with return code {}".format(
        cmd_id,
        child_process.returncode,
    ))

    result = RunResult()
    result.duration = datetime.utcnow() - start
    result.stdout = stdout_lb.record.getvalue()
    result.stderr = stderr_lb.record.getvalue()
    result.return_code = child_process.returncode
    return result


def run(
    hostname,
    command,
    add_host_keys=False,
    data_stdin=None,
    ignore_failure=False,
    raise_for_return_codes=(
        126,  # command not executable
        127,  # command not found
        255,  # SSH error
    ),
    log_function=None,
    username=None,  # SSH auth
    wrapper_inner="{}",
    wrapper_outer="{}",
    user="root",  # remote user running the command
):
    """
    Runs a command on a remote system.
    """
    shell_command = wrapper_outer.format(quote(wrapper_inner.format(command)), user)

    ssh_command = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "KbdInteractiveAuthentication=no",
        "-o", "PasswordAuthentication=no",
        "-o", "StrictHostKeyChecking=no" if add_host_keys else "StrictHostKeyChecking=yes",
    ]
    if username:
        ssh_command += ["-l", str(username)]
    extra_args = environ.get("BW_SSH_ARGS", "").strip()
    if extra_args:
        ssh_command.extend(split(extra_args))
    ssh_command.append(hostname)
    ssh_command.append(shell_command)

    result = run_local(
        ssh_command,
        data_stdin=data_stdin,
        log_function=log_function,
    )

    if result.return_code != 0:
        error_msg = _(
            "Non-zero return code ({rcode}) running '{command}' "
            "on '{host}':\n\n{result}\n\n"
        ).format(
            command=command,
            host=hostname,
            rcode=result.return_code,
            result=force_text(result.stdout) + force_text(result.stderr),
        )
        io.debug(error_msg)
        if not ignore_failure or result.return_code in raise_for_return_codes:
            raise RemoteException(error_msg)
    return result


def run_routeros(hostname, username, password, *args):
    with ROUTEROS_CONNECTIONS_LOCK:
        try:
            conn_state = ROUTEROS_CONNECTIONS[hostname]
        except KeyError:
            conn_state = {
                'connection': None,
                'lock': Lock(),
                'needs_reconnect': True,
            }
            ROUTEROS_CONNECTIONS[hostname] = conn_state

    with conn_state['lock']:
        if conn_state['needs_reconnect']:
            if conn_state['connection']:
                try:
                    conn_state['connection'].close()
                except Exception as exc:
                    io.debug(f'error closing RouterOS connection to {hostname}: {exc}')

            try:
                conn_state['connection'] = connect(
                    # str() to resolve Faults
                    username=str(username),
                    password=str(password or ""),
                    host=hostname,
                    timeout=120.0,
                )
            except Exception as e:
                raise RemoteException(str(e)) from e
            else:
                conn_state['needs_reconnect'] = False

        try:
            io.debug(f'{hostname}: running routeros command: {repr(args)}')
            result = tuple(conn_state['connection'].rawCmd(*args))
        except Exception as e:
            # Connection in unknown state, mark it as broken
            conn_state['needs_reconnect'] = True
            raise RemoteException(str(e)) from e

    run_result = RunResult()
    run_result.raw = result
    run_result.stdout = repr(result)
    run_result.stderr = ""
    return run_result


def upload(
    hostname,
    local_path,
    remote_path,
    add_host_keys=False,
    group="",
    mode=None,
    owner="",
    ignore_failure=False,
    username=None,
    wrapper_inner="{}",
    wrapper_outer="{}",
):
    """
    Upload a file.
    """
    io.debug(_("uploading {path} -> {host}:{target}").format(
        host=hostname, path=local_path, target=remote_path))
    temp_filename = ".bundlewrap_tmp_" + randstr()

    scp_hostname = hostname
    if ':' in hostname:
        scp_hostname = f"[{hostname}]"

    scp_command = [
        "scp",
        "-o", "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no" if add_host_keys else "StrictHostKeyChecking=yes",
    ]
    extra_args = environ.get("BW_SCP_ARGS", environ.get("BW_SSH_ARGS", "")).strip()
    if extra_args:
        scp_command.extend(split(extra_args))
    scp_command.append(local_path)
    if username:
        scp_command.append(f"{username}@{scp_hostname}:{temp_filename}")
    else:
        scp_command.append(f"{scp_hostname}:{temp_filename}")

    scp_process = run_local(scp_command)

    if scp_process.return_code != 0:
        if ignore_failure:
            return False
        raise RemoteException(_(
            "Upload to {host} failed for {failed}:\n\n{result}\n\n"
        ).format(
            failed=remote_path,
            host=hostname,
            result=force_text(scp_process.stdout) + force_text(scp_process.stderr),
        ))

    if owner or group:
        if group:
            group = ":" + quote(group)
        result = run(
            hostname,
            "chown {}{} {}".format(
                quote(owner),
                group,
                quote(temp_filename),
            ),
            add_host_keys=add_host_keys,
            ignore_failure=ignore_failure,
            username=username,
            wrapper_inner=wrapper_inner,
            wrapper_outer=wrapper_outer,
        )
        if result.return_code != 0:
            return False

    if mode:
        result = run(
            hostname,
            "chmod {} {}".format(
                mode,
                quote(temp_filename),
            ),
            add_host_keys=add_host_keys,
            ignore_failure=ignore_failure,
            username=username,
            wrapper_inner=wrapper_inner,
            wrapper_outer=wrapper_outer,
        )
        if result.return_code != 0:
            return False

    result = run(
        hostname,
        "mv -f {} {}".format(
            quote(temp_filename),
            quote(remote_path),
        ),
        add_host_keys=add_host_keys,
        ignore_failure=ignore_failure,
        username=username,
        wrapper_inner=wrapper_inner,
        wrapper_outer=wrapper_outer,
    )
    return result.return_code == 0
