import platform
from subprocess import Popen, PIPE

from ..bundle import FILENAME_BUNDLE
from ..secrets import FILENAME_SECRETS


HOST_OS = {
    "Darwin": 'macos',
    "Linux": 'linux',
}


def host_os():
    return HOST_OS[platform.system()]


def make_repo(tmpdir, bundles=None, groups=None, nodes=None):
    bundles = {} if bundles is None else bundles
    groups = {} if groups is None else groups
    nodes = {} if nodes is None else nodes

    bundles_dir = tmpdir.mkdir("bundles")
    for bundle, items in bundles.items():
        bundle_dir = bundles_dir.mkdir(bundle)
        bundle_dir.mkdir("files")
        bundlepy = bundle_dir.join(FILENAME_BUNDLE)
        bundle_content = ""
        for itemtype, itemconfig in items.items():
            bundle_content += "{} = {}\n".format(itemtype, repr(itemconfig))
        bundlepy.write(bundle_content)

    tmpdir.mkdir("data")
    tmpdir.mkdir("hooks")

    groupspy = tmpdir.join("groups.py")
    groupspy.write("groups = {}\n".format(repr(groups)))

    nodespy = tmpdir.join("nodes.py")
    nodespy.write("nodes = {}\n".format(repr(nodes)))

    secrets = tmpdir.join(FILENAME_SECRETS)
    secrets.write("[generate]\nkey = {}\n\n[encrypt]\nkey = {}\n".format(
        "Fl53iG1czBcaAPOKhSiJE7RjFU9nIAGkiKDy0k_LoTc=",
        "DbYiUu5VMfrdeSiKYiAH4rDOAUISipvLSBJI-T0SpeY=",
    ))


def run(command, path=None):
    process = Popen(command, cwd=path, shell=True, stderr=PIPE, stdout=PIPE)
    stdout, stderr = process.communicate()
    print(stdout.decode('utf-8'))
    print(stderr.decode('utf-8'))
    return (stdout, stderr, process.returncode)
