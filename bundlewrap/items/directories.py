from collections import defaultdict
from os.path import normpath
from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.remote import PathInfo
from bundlewrap.utils.text import mark_for_translation as _
from bundlewrap.utils.text import is_subdirectory
from bundlewrap.utils.ui import io


UNMANAGED_PATH_DESC = _("unmanaged subpaths")


def validator_mode(item_id, value):
    if value is None:
        return

    value = str(value)
    if not value.isdigit():
        raise BundleError(
            _("mode for {item} should be written as digits, got: '{value}'"
              "").format(item=item_id, value=value)
        )
    for digit in value:
        if int(digit) > 7 or int(digit) < 0:
            raise BundleError(_(
                "invalid mode for {item}: '{value}'"
            ).format(item=item_id, value=value))
    if not len(value) == 3 and not len(value) == 4:
        raise BundleError(_(
            "mode for {item} should be three or four digits long, was: '{value}'"
        ).format(item=item_id, value=value))


ATTRIBUTE_VALIDATORS = defaultdict(lambda: lambda id, value: None)
ATTRIBUTE_VALIDATORS.update({
    'mode': validator_mode,
})


class Directory(Item):
    """
    A directory.
    """
    BUNDLE_ATTRIBUTE_NAME = "directories"
    ITEM_ATTRIBUTES = {
        'group': "root",
        'mode': "0755",
        'owner': "root",
        'purge': False,
    }
    ITEM_TYPE_NAME = "directory"

    def __repr__(self):
        return "<Directory path:{}>".format(
            quote(self.name),
        )

    def cdict(self):
        cdict = {
            'paths_to_purge': [],
            'type': 'directory',
        }
        for optional_attr in ('group', 'mode', 'owner'):
            if self.attributes[optional_attr] is not None:
                cdict[optional_attr] = self.attributes[optional_attr]
        return cdict

    def display_dicts(self, cdict, sdict, keys):
        try:
            keys.remove('paths_to_purge')
        except ValueError:
            pass
        else:
            keys.append(UNMANAGED_PATH_DESC)
            cdict[UNMANAGED_PATH_DESC] = cdict['paths_to_purge']
            sdict[UNMANAGED_PATH_DESC] = sdict['paths_to_purge']
            del cdict['paths_to_purge']
            del sdict['paths_to_purge']
        return (cdict, sdict, keys)

    def fix(self, status):
        if status.must_be_created or 'type' in status.keys_to_fix:
            # fixing the type fixes everything
            self._fix_type(status)
            return

        for path in status.sdict.get('paths_to_purge', []):
            self.run("rm -rf -- {}".format(quote(path)))

        for fix_type in ('mode', 'owner', 'group'):
            if fix_type in status.keys_to_fix:
                if fix_type == 'group' and 'owner' in status.keys_to_fix:
                    # owner and group are fixed with a single chown
                    continue
                getattr(self, "_fix_" + fix_type)(status)

    def _fix_mode(self, status):
        if self.node.os in self.node.OS_FAMILY_BSD:
            chmod_command = "chmod {} {}"
        else:
            chmod_command = "chmod {} -- {}"
        self.run(chmod_command.format(
            self.attributes['mode'],
            quote(self.name),
        ))

        if self.node.os not in self.node.OS_FAMILY_BSD:
            # The bits S_ISUID and S_ISGID are special. POSIX says,
            # if they are NOT set, the implementation of "chmod" may or
            # may not clear them. This means that "chmod 0755 foodir"
            # does not necessarily clear the S_ISUID and/or S_ISGID bit,
            # while a "chmod 6755 foodir" will always set them.
            #
            # GNU coreutils have decided to actually behave this way.
            # You can't clear a S_ISUID or S_ISGID bit by issuing "chmod
            # 0755 foodir". You must explicitly do a "chmod u-s foodir"
            # or "chmod g-s foodir".
            #
            # This does not apply to regular files, nor to the sticky
            # bit (S_ISVTX). Also, FreeBSD, NetBSD, and OpenBSD do clear
            # these bits on "chmod 0755 foodir".

            # We only want to run these extra commands if we have found
            # one of the two special bits to be set.
            if status.sdict is not None and int(status.sdict['mode'], 8) & 0o6000:
                if not int(self.attributes['mode'], 8) & 0o4000:
                    self.run("chmod u-s {}".format(quote(self.name)))
                if not int(self.attributes['mode'], 8) & 0o2000:
                    self.run("chmod g-s {}".format(quote(self.name)))

    def _fix_owner(self, status):
        group = self.attributes['group'] or ""
        if group:
            group = ":" + quote(group)
        if self.node.os in self.node.OS_FAMILY_BSD:
            command = "chown {}{} {}"
        else:
            command = "chown {}{} -- {}"
        self.run(command.format(
            quote(self.attributes['owner'] or ""),
            group,
            quote(self.name),
        ))
    _fix_group = _fix_owner

    def _fix_type(self, status):
        self.run("rm -rf -- {}".format(quote(self.name)))
        self.run("mkdir -p -- {}".format(quote(self.name)))
        if self.attributes['mode']:
            self._fix_mode(status)
        if self.attributes['owner'] or self.attributes['group']:
            self._fix_owner(status)

    def _get_paths_to_purge(self):
        result = self.run("find {} -maxdepth 1 -print0".format(quote(self.name)))
        for line in result.stdout.split(b"\0"):
            line = line.decode('utf-8')
            for item_type in ('directory', 'file', 'symlink'):
                for item in self.node.items:
                    if (
                        item.id == "{}:{}".format(item_type, line) or
                        item.id.startswith("{}:{}/".format(item_type, line))
                    ):
                        break
                else:
                    continue
                break
            else:
                # this file or directory is not managed
                io.debug((
                    "found unmanaged path below {dirpath} on {node}, "
                    "marking for removal: {path}"
                ).format(
                    dirpath=self.name,
                    node=self.node.name,
                    path=line,
                ))
                yield line

    def get_auto_deps(self, items):
        deps = []
        for item in items:
            if item == self:
                continue
            if ((
                    item.ITEM_TYPE_NAME == "file" and
                    is_subdirectory(item.name, self.name)
                ) or (
                    item.ITEM_TYPE_NAME in ("file", "symlink") and
                    item.name == self.name
            )):
                raise BundleError(_(
                    "{item1} (from bundle '{bundle1}') blocking path to "
                    "{item2} (from bundle '{bundle2}')"
                ).format(
                    item1=item.id,
                    bundle1=item.bundle.name,
                    item2=self.id,
                    bundle2=self.bundle.name,
                ))
            elif item.ITEM_TYPE_NAME == "user" and item.name == self.attributes['owner']:
                if item.attributes['delete']:
                    raise BundleError(_(
                        "{item1} (from bundle '{bundle1}') depends on item "
                        "{item2} (from bundle '{bundle2}') which is set to be deleted"
                    ).format(
                        item1=self.id,
                        bundle1=self.bundle.name,
                        item2=item.id,
                        bundle2=item.bundle.name,
                    ))
                else:
                    deps.append(item.id)
            elif item.ITEM_TYPE_NAME == "group" and item.name == self.attributes['group']:
                if item.attributes['delete']:
                    raise BundleError(_(
                        "{item1} (from bundle '{bundle1}') depends on item "
                        "{item2} (from bundle '{bundle2}') which is set to be deleted"
                    ).format(
                        item1=self.id,
                        bundle1=self.bundle.name,
                        item2=item.id,
                        bundle2=item.bundle.name,
                    ))
                else:
                    deps.append(item.id)
            elif item.ITEM_TYPE_NAME in ("directory", "symlink"):
                if is_subdirectory(item.name, self.name):
                    deps.append(item.id)
        return deps

    def sdict(self):
        path_info = PathInfo(self.node, self.name)
        if not path_info.exists:
            return None
        else:
            paths_to_purge = []
            if self.attributes['purge']:
                paths_to_purge = list(self._get_paths_to_purge())
            return {
                'type': 'directory' if path_info.is_directory else path_info.stat['type'],
                'mode': path_info.mode,
                'owner': path_info.owner,
                'group': path_info.group,
                'paths_to_purge': paths_to_purge,
            }

    def patch_attributes(self, attributes):
        if 'mode' in attributes and attributes['mode'] is not None:
            attributes['mode'] = str(attributes['mode']).zfill(4)
        if 'group' not in attributes and self.node.os in self.node.OS_FAMILY_BSD:
            # BSD doesn't have a root group, so we have to use a
            # different default value here
            attributes['group'] = 'wheel'
        return attributes

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        for key, value in attributes.items():
            ATTRIBUTE_VALIDATORS[key](item_id, value)

    @classmethod
    def validate_name(cls, bundle, name):
        if normpath(name) != name:
            raise BundleError(_(
                "'{path}' is an invalid directory path, "
                "should be '{normpath}' (bundle '{bundle}')"
            ).format(
                bundle=bundle.name,
                normpath=normpath(name),
                path=name,
            ))
