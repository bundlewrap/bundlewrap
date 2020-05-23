from datetime import datetime
from shlex import quote
from select import select
from shlex import split
from subprocess import Popen, PIPE
from threading import Event, Thread
from os import close, environ, pipe, read, setpgrp

from .exceptions import RemoteException
from .utils import cached_property
from .utils.text import force_text, LineBuffer, mark_for_translation as _, randstr
from .utils.ui import io


def output_thread_body(line_buffer, read_fd, quit_event, read_until_eof):
    # see run() for details
    while True:
        r, w, x = select([read_fd], [], [], 0.1)
        if r:
            chunk = read(read_fd, 1024)
            if chunk:
                line_buffer.write(chunk)
            else:  # EOF
                return
        elif quit_event.is_set() and not read_until_eof:
            # one last chance to read output after the child process
            # has died
            while True:
                r, w, x = select([read_fd], [], [], 0)
                if r:
                    line_buffer.write(read(read_fd, 1024))
                else:
                    break
            return


def download(
    hostname,
    remote_path,
    local_path,
    add_host_keys=False,
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
    # LineBuffers during `bw run`.
    stdout_fd_r, stdout_fd_w = pipe()
    stderr_fd_r, stderr_fd_w = pipe()

    cmd_id = randstr(length=4).upper()
    io.debug("running command with ID {}: {}".format(cmd_id, " ".join(command)))
    start = datetime.utcnow()

    # Launch the child process. It's important that SSH gets a dummy
    # stdin, i.e. it must *not* read from the terminal. Otherwise, it
    # can steal user input.
    child_process = Popen(
        command,
        preexec_fn=setpgrp,
        shell=shell,
        stdin=PIPE,
        stderr=stderr_fd_w,
        stdout=stdout_fd_w,
    )
    io._child_pids.append(child_process.pid)

    if data_stdin is not None:
        child_process.stdin.write(data_stdin)

    quit_event = Event()
    stdout_thread = Thread(
        args=(stdout_lb, stdout_fd_r, quit_event, True),
        target=output_thread_body,
    )
    stderr_thread = Thread(
        args=(stderr_lb, stderr_fd_r, quit_event, False),
        target=output_thread_body,
    )
    stdout_thread.start()
    stderr_thread.start()

    try:
        child_process.communicate()
    finally:
        # Once we end up here, the child process has terminated.
        #
        # Now, the big question is: Why do we need an Event here?
        #
        # Problem is, a user could use SSH multiplexing with
        # auto-forking (e.g., "ControlPersist 10m"). In this case,
        # OpenSSH forks another process which holds the "master"
        # connection. This forked process *inherits* our pipes (at least
        # for stderr). Thus, only when that master process finally
        # terminates (possibly after many minutes), we will be informed
        # about EOF on our stderr pipe. That doesn't work. bw will hang.
        #
        # So, instead, we use a busy loop in output_thread_body() which
        # checks for quit_event being set. Unfortunately there is no way
        # to be absolutely sure that we received all output from stderr
        # because we never get a proper EOF there. All we can do is hope
        # that all output has arrived on the reading end of the pipe by
        # the time the quit_event is checked in the thread.
        #
        # Luckily stdout is a somewhat simpler affair: we can just close
        # the writing end of the pipe, causing the reader thread to
        # shut down as it sees the EOF.
        io._child_pids.remove(child_process.pid)
        quit_event.set()
        close(stdout_fd_w)
        stdout_thread.join()
        stderr_thread.join()
        stdout_lb.close()
        stderr_lb.close()
        for fd in (stdout_fd_r, stderr_fd_r, stderr_fd_w):
            close(fd)

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
    wrapper_inner="{}",
    wrapper_outer="{}",
):
    """
    Runs a command on a remote system.
    """
    ssh_command = [
        "ssh",
        "-o", "KbdInteractiveAuthentication=no",
        "-o", "PasswordAuthentication=no",
        "-o", "StrictHostKeyChecking=no" if add_host_keys else "StrictHostKeyChecking=yes",
    ]
    extra_args = environ.get("BW_SSH_ARGS", "").strip()
    if extra_args:
        ssh_command.extend(split(extra_args))
    ssh_command.append(hostname)
    ssh_command.append(wrapper_outer.format(quote(wrapper_inner.format(command))))

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


def upload(
    hostname,
    local_path,
    remote_path,
    add_host_keys=False,
    group="",
    mode=None,
    owner="",
    ignore_failure=False,
    wrapper_inner="{}",
    wrapper_outer="{}",
):
    """
    Upload a file.
    """
    io.debug(_("uploading {path} -> {host}:{target}").format(
        host=hostname, path=local_path, target=remote_path))
    temp_filename = ".bundlewrap_tmp_" + randstr()

    scp_command = [
        "scp",
        "-o",
        "StrictHostKeyChecking=no" if add_host_keys else "StrictHostKeyChecking=yes",
    ]
    extra_args = environ.get("BW_SCP_ARGS", environ.get("BW_SSH_ARGS", "")).strip()
    if extra_args:
        scp_command.extend(split(extra_args))
    scp_command.append(local_path)
    scp_command.append("{}:{}".format(hostname, temp_filename))

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
        wrapper_inner=wrapper_inner,
        wrapper_outer=wrapper_outer,
    )
    return result.return_code == 0
