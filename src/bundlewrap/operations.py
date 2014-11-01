# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from base64 import b64decode
from pipes import quote
from stat import S_IRUSR, S_IWUSR

from .exceptions import RemoteException
from .utils import LOG
from .utils.text import force_text, mark_for_translation as _, randstr
from .utils.ui import LineBuffer


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
                error=,
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


def run(hostname, command, ignore_failure=False, stderr=None,
        stdout=None, password=None, pty=False, sudo=True):
    """
    Runs a command on a remote system.
    """
    if stderr is None:
        stderr = LineBuffer(lambda s: None)
    if stdout is None:
        stdout = LineBuffer(lambda s: None)

    LOG.debug("running on {host}: {command}".format(command=command, host=hostname))

    #export LANG=C

    LOG.debug("command finished with return code {}".format())

    if not XXX_SUCCESS and not ignore_failure:
        raise RemoteException(_(
            "Non-zero return code ({rcode}) running '{command}' on '{host}':\n\n{result}"
        ).format(
            command=command,
            host=hostname,
            rcode=,
            result=force_text() + force_text(),
        ))

    result = RunResult()
    result.stdout = force_text()
    result.stderr = force_text()
    result.return_code =
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
