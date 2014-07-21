from pipes import quote

from . import cached_property, LOG
from .text import mark_for_translation as _


def _parse_file_output(file_output):
    if file_output.startswith("cannot open `"):
        return ('nonexistent', "")
    elif file_output in ("directory", "sticky directory"):
        return ('directory', file_output)
    elif file_output in ("block special", "character special"):
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
    if result.return_code != 0:
        return ('nonexistent', "")
    file_output = result.stdout.strip()
    return _parse_file_output(file_output)


def stat(node, path):
    result = node.run("stat --printf '%U:%G:%a:%s' -- {}".format(quote(path)))
    owner, group, mode, size = result.stdout.split(":")
    mode = mode.zfill(4)
    file_stat = {
        'owner': owner,
        'group': group,
        'mode': mode,
        'size': int(size),
    }
    LOG.debug(_("stat for '{path}' on {node}: {result}".format(
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
        result = self.node.run("sha1sum -- " + quote(self.path))
        return result.stdout.strip().split()[0]

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
