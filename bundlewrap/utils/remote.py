# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from . import cached_property
from .text import force_text, mark_for_translation as _
from .ui import io


def _parse_file_output(file_output):
    if file_output.startswith("cannot open "):
        # required for Mac OS X, OpenBSD, and CentOS/RHEL
        return ('nonexistent', "")
    elif file_output.endswith("directory"):
        return ('directory', file_output)
    elif file_output.startswith("block special") or \
            file_output.startswith("character special"):
        return ('other', file_output)
    elif file_output.startswith("symbolic link to ") or \
            file_output.startswith("broken symbolic link to "):
        return ('symlink', file_output)
    else:
        return ('file', file_output)


def get_path_type(node, path):
    """
    Returns (TYPE, DESC) where TYPE is one of:

        'directory', 'file', 'nonexistent', 'other', 'symlink'

    and DESC is the output of the 'file' command line utility.
    """
    result = node.run("file -bh -- {}".format(quote(path)), may_fail=True)
    file_output = force_text(result.stdout.strip())
    if (
        result.return_code != 0 or
        "No such file or directory" in file_output  # thanks CentOS
    ):
        return ('nonexistent', "")

    return _parse_file_output(file_output)


def stat(node, path):
    if node.os in node.OS_FAMILY_BSD:
        result = node.run("stat -f '%Su:%Sg:%p:%z' -- {}".format(quote(path)))
    else:
        result = node.run("stat -c '%U:%G:%a:%s' -- {}".format(quote(path)))
    owner, group, mode, size = force_text(result.stdout).split(":")
    mode = mode[-4:].zfill(4)  # cut off BSD file type
    file_stat = {
        'owner': owner,
        'group': group,
        'mode': mode,
        'size': int(size),
    }
    io.debug(_("stat for '{path}' on {node}: {result}".format(
        node=node.name,
        path=path,
        result=repr(file_stat),
    )))
    return file_stat


class PathInfo(object):
    """
    Serves as a proxy to get_path_type.
    """
    def __init__(self, node, path):
        self.node = node
        self.path = path
        self.path_type, self.desc = get_path_type(node, path)
        self.stat = stat(node, path) if self.path_type != 'nonexistent' else {}

    def __repr__(self):
        return "<PathInfo for {}:{}>".format(self.node.name, quote(self.path))

    @property
    def exists(self):
        return self.path_type != 'nonexistent'

    @property
    def group(self):
        return self.stat['group']

    @property
    def is_binary_file(self):
        return self.is_file and not self.is_text_file

    @property
    def is_directory(self):
        return self.path_type == 'directory'

    @property
    def is_file(self):
        return self.path_type == 'file'

    @property
    def is_symlink(self):
        return self.path_type == 'symlink'

    @property
    def is_text_file(self):
        return self.is_file and (
            "text" in self.desc or
            self.desc in (
                          "empty",
                          "OpenSSH RSA public key",
                          "OpenSSH DSA public key",
                         )
        )

    @property
    def mode(self):
        return self.stat['mode']

    @property
    def owner(self):
        return self.stat['owner']

    @cached_property
    def sha1(self):
        if self.node.os == 'macos':
            result = self.node.run("shasum -a 1 -- {}".format(quote(self.path)))
        elif self.node.os in self.node.OS_FAMILY_BSD:
            result = self.node.run("sha1 -q -- {}".format(quote(self.path)))
        else:
            result = self.node.run("sha1sum -- {}".format(quote(self.path)))
        return force_text(result.stdout).strip().split()[0]

    @property
    def size(self):
        return self.stat['size']

    @property
    def symlink_target(self):
        if not self.is_symlink:
            raise ValueError("{} is not a symlink".format(quote(self.path)))
        if self.desc.startswith("symbolic link to `"):
            return self.desc[18:-1]
        elif self.desc.startswith("broken symbolic link to `"):
            return self.desc[25:-1]
        elif self.desc.startswith("symbolic link to "):
            return self.desc[17:]
        elif self.desc.startswith("broken symbolic link to "):
            return self.desc[24:]
        else:
            raise ValueError("unable to find target for {}".format(quote(self.path)))
