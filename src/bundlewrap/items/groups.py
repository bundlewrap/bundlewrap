# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bundlewrap.exceptions import BundleError
from bundlewrap.items import BUILTIN_ITEM_ATTRIBUTES, Item, ItemStatus
from bundlewrap.items.users import _USERNAME_VALID_CHARACTERS
from bundlewrap.utils import LOG
from bundlewrap.utils.text import mark_for_translation as _
from bundlewrap.utils.text import bold


def _parse_group_line(line):
    """
    Parses a line from /etc/group and returns the information as a
    dictionary.
    """
    result = dict(zip(
        ('groupname', 'password', 'gid', 'members'),
        line.strip().split(":"),
    ))
    result['gid'] = int(result['gid'])
    del result['password']  # nothing useful here
    return result


class Group(Item):
    """
    A group.
    """
    BUNDLE_ATTRIBUTE_NAME = "groups"
    ITEM_ATTRIBUTES = {
        'delete': False,
        'gid': None,
    }
    ITEM_TYPE_NAME = "group"
    REQUIRED_ATTRIBUTES = []

    def __repr__(self):
        return "<Group name:{}>".format(self.name)

    def ask(self, status):
        if not status.info['exists']:
            return _("'{}' not found in /etc/group").format(self.name)
        elif self.attributes['delete']:
            return _("'{}' found in /etc/group. Will be deleted.").format(self.name)
        else:
            return "{} {} → {}\n".format(
                bold(_("GID")),
                status.info['gid'],
                self.attributes['gid'],
            )

    def fix(self, status):
        if not status.info['exists']:
            LOG.info(_("{node}:{bundle}:{item}: creating...").format(
                bundle=self.bundle.name,
                item=self.id,
                node=self.node.name,
            ))
            if self.attributes['gid'] is None:
                command = "groupadd {}".format(self.name)
            else:
                command = "groupadd -g {gid} {groupname}".format(
                    gid=self.attributes['gid'],
                    groupname=self.name,
                )
            self.node.run(command, may_fail=True)
        elif self.attributes['delete']:
            LOG.info(_("{node}:{bundle}:{item}: deleting...").format(
                bundle=self.bundle.name,
                item=self.id,
                node=self.node.name,
            ))
            self.node.run("groupdel {}".format(self.name), may_fail=True)
        else:
            LOG.info(_("{node}:{bundle}:{item}: updating...").format(
                bundle=self.bundle.name,
                item=self.id,
                node=self.node.name,
            ))
            self.node.run(
                "groupmod -g {gid} {groupname}".format(
                    gid=self.attributes['gid'],
                    groupname=self.name,
                ),
                may_fail=True,
            )

    def get_status(self):
        # verify content of /etc/group
        grep_result = self.node.run(
            "grep -e '^{}:' /etc/group".format(self.name),
            may_fail=True,
        )
        if grep_result.return_code != 0:
            return ItemStatus(correct=self.attributes['delete'], info={'exists': False})

        status = ItemStatus(correct=not self.attributes['delete'], info={'exists': True})
        status.info.update(_parse_group_line(grep_result.stdout))

        if self.attributes['gid'] is not None and \
                status.info['gid'] != self.attributes['gid']:
            status.correct = False

        return status

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if attributes.get('delete', False):
            for attr in attributes.keys():
                if attr not in ['delete'] + list(BUILTIN_ITEM_ATTRIBUTES.keys()):
                    raise BundleError(_(
                        "{item} from bundle '{bundle}' cannot have other "
                        "attributes besides 'delete'"
                    ).format(item=item_id, bundle=bundle.name))

    @classmethod
    def validate_name(cls, bundle, name):
        for char in name:
            if char not in _USERNAME_VALID_CHARACTERS:
                raise BundleError(_(
                    "Invalid character in group name '{name}': {char} (bundle '{bundle}')"
                ).format(
                    char=char,
                    bundle=bundle.name,
                    name=name,
                ))

        if name.endswith("_") or name.endswith("-"):
            raise BundleError(_(
                "Group name '{name}' must not end in dash or underscore (bundle '{bundle}')"
            ).format(
                bundle=bundle.name,
                name=name,
            ))

        if len(name) > 30:
            raise BundleError(_(
                "Group name '{name}' is longer than 30 characters (bundle '{bundle}')"
            ).format(
                bundle=bundle.name,
                name=name,
            ))
