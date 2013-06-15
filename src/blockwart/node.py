from paramiko.client import SSHClient

from .utils import cached_property


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
        self.name = name
        self.repo = repo
        if 'hostname' in infodict:
            self.hostname = infodict['hostname']
        else:
            self.hostname = self.name

    @cached_property
    def _ssh_client(self):
        client = SSHClient()
        client.load_system_host_keys()
        client.connect(self.hostname)
        return client

    @cached_property
    def groups(self):
        return self.repo.groups_for_node(self)

    def run(self, command, stdin=None):
        chan = self._ssh_client.get_transport().open_session()
        chan.get_pty()
        chan.exec_command(command)
        fstdin = chan.makefile('wb', -1)
        fstdout = chan.makefile('rb', -1)
        fstderr = chan.makefile_stderr('rb', -1)
        if stdin is not None:
            fstdin.write(stdin)
            fstdin.flush()
        result = RunResult()
        result.stdout = fstdout.read()
        result.stderr = fstderr.read()
        result.returncode = chan.recv_exit_status()
        return result
