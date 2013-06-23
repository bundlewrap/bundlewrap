from paramiko.client import SSHClient, WarningPolicy

from .bundle import Bundle
from .exceptions import RepositoryError
from .utils import cached_property, mark_for_translation as _, validate_name


class RunResult(object):
    def __init__(self):
        self.returncode = None
        self.stderr = None
        self.stdout = None

    def __str__(self):
        return self.stdout


class Node(object):
    def __init__(self, repo, name, infodict=None):
        if infodict is None:
            infodict = {}

        if not validate_name(name):
            raise RepositoryError(_("'{}' is not a valid node name"))

        self.name = name
        self.repo = repo
        self.hostname = infodict.get('hostname', self.name)

    def __cmp__(self, other):
        return cmp(self.name, other.name)

    @cached_property
    def _ssh_client(self):
        client = SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(WarningPolicy())
        client.connect(self.hostname)
        return client

    @cached_property
    def bundles(self):
        for group in self.groups:
            for bundle_name in group.bundle_names:
                yield Bundle(self, bundle_name)

    @cached_property
    def groups(self):
        return self.repo.groups_for_node(self)

    @property
    def items(self):
        for bundle in self.bundles:
            for item in bundle.items:
                yield item

    def run(self, command, sudo=True):
        chan = self._ssh_client.get_transport().open_session()
        chan.get_pty()
        if sudo:
            command = "sudo " + command
        chan.exec_command(command)
        fstdout = chan.makefile('rb', -1)
        fstderr = chan.makefile_stderr('rb', -1)
        result = RunResult()
        result.stdout = fstdout.read()
        result.stderr = fstderr.read()
        result.returncode = chan.recv_exit_status()
        return result
