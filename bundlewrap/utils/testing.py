import platform
from subprocess import Popen, PIPE

from ..bundle import FILENAME_BUNDLE, FILENAME_ITEMS
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
    for bundle, attrs_and_items in bundles.items():
        for key in attrs_and_items:
            assert key in ("items", "attrs")
        bundle_dir = bundles_dir.mkdir(bundle)
        bundle_dir.mkdir("files")
        bundlepy = bundle_dir.join(FILENAME_BUNDLE)
        itemspy = bundle_dir.join(FILENAME_ITEMS)

        items_content = ""
        for itemtype, itemconfig in attrs_and_items.get('items', {}).items():
            items_content += "{} = {}\n".format(itemtype, repr(itemconfig))
        itemspy.write(items_content)

        bundle_content = ""
        for attrname, attrvalue in attrs_and_items.get('attrs', {}).items():
            bundle_content += "{} = {}\n".format(attrname, repr(attrvalue))
        bundlepy.write(bundle_content)

    tmpdir.mkdir("data")
    tmpdir.mkdir("hooks")
    tmpdir.mkdir("libs")

    groupspy = tmpdir.join("groups.py")
    if groups:
        groupspy.write("groups = {}\n".format(repr(groups)))
    else:
        groupspy.write("\n")

    nodespy = tmpdir.join("nodes.py")
    if nodes:
        nodespy.write("nodes = {}\n".format(repr(nodes)))
    else:
        nodespy.write("\n")

    secrets = tmpdir.join(FILENAME_SECRETS)
    secrets.write("""
[generate]
key = Fl53iG1czBcaAPOKhSiJE7RjFU9nIAGkiKDy0k_LoTc=

[encrypt]
key = DbYiUu5VMfrdeSiKYiAH4rDOAUISipvLSBJI-T0SpeY=

[command]
key_command = echo -e foo\\\\nDbYiUu5VMfrdeSiKYiAH4rDOAUISipvLSBJI-T0SpeY= | tail -n 1
""")


def run(command, path=None):
    process = Popen(command, cwd=path, shell=True, stderr=PIPE, stdout=PIPE)
    stdout, stderr = process.communicate()
    print(stdout.decode('utf-8'))
    print(stderr.decode('utf-8'))
    return (stdout, stderr, process.returncode)
