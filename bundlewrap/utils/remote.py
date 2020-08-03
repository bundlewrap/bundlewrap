from shlex import quote

from . import cached_property
from .text import force_text, mark_for_translation as _
from .ui import io


def stat(node, path):
    if node.os in node.OS_FAMILY_BSD:
        result = node.run(
            "stat -f '%Su:%Sg:%p:%z:%HT' -- {}".format(quote(path)),
            may_fail=True,
        )
    else:
        result = node.run(
            "stat -c '%U:%G:%a:%s:%F' -- {}".format(quote(path)),
            may_fail=True,
        )
    if result.return_code != 0:
        return {}
    owner, group, mode, size, ftype = \
        force_text(result.stdout).strip().split(":", 5)
    mode = mode[-4:].zfill(4)  # cut off BSD file type
    file_stat = {
        'owner': owner,
        'group': group,
        'mode': mode,
        'size': int(size),
        'type': ftype.lower(),
    }
    io.debug(_("stat for '{path}' on {node}: {result}".format(
        node=node.name,
        path=path,
        result=repr(file_stat),
    )))
    return file_stat


class PathInfo:
    """
    Serves as a proxy to get_path_type.
    """

    def __init__(self, node, path):
        self.node = node
        self.path = path
        self.stat = stat(node, path)

    def __repr__(self):
        return "<PathInfo for {}:{}>".format(self.node.name, quote(self.path))

    @property
    def exists(self):
        return bool(self.stat)

    @property
    def group(self):
        return self.stat['group']

    @property
    def is_directory(self):
        return self.stat['type'] == "directory"

    @property
    def is_file(self):
        return self.stat['type'] in ("regular file", "regular empty file")

    @property
    def is_symlink(self):
        return self.stat['type'] == "symbolic link"

    @property
    def is_text_file(self):
        return self.is_file and (
            "text" in self.desc or
            self.desc in (
                "empty",
                "JSON data",
                "OpenSSH ED25519 public key",
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
    def desc(self):
        return force_text(self.node.run(
            "file -bh -- {}".format(quote(self.path))
        ).stdout).strip()

    @cached_property
    def sha1(self):
        if self.node.os == 'macos':
            result = self.node.run("shasum -a 1 -- {}".format(quote(self.path)))
        elif self.node.os in self.node.OS_FAMILY_BSD:
            result = self.node.run("sha1 -q -- {}".format(quote(self.path)))
        else:
            result = self.node.run("sha1sum -- {}".format(quote(self.path)))
        # sha1sum adds a leading backslash to hashes of files whose name
        # contains backslash-escaped characters – we must lstrip() that
        return force_text(result.stdout).strip().lstrip("\\").split()[0]

    @property
    def size(self):
        return self.stat['size']

    @property
    def symlink_target(self):
        if not self.is_symlink:
            raise ValueError("{} is not a symlink".format(quote(self.path)))

        return force_text(self.node.run(
            "readlink -- {}".format(quote(self.path)), may_fail=True,
        ).stdout.strip())
