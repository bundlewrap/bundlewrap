# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from blockwart.exceptions import BundleError
from blockwart.items import Item, ItemStatus
from blockwart.items.users import _USERNAME_VALID_CHARACTERS
from blockwart.utils.text import mark_for_translation as _
from blockwart.utils.text import bold


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
    DEPENDS_STATIC = []
    ITEM_ATTRIBUTES = {
        'gid': None,
    }
    ITEM_TYPE_NAME = "group"
    REQUIRED_ATTRIBUTES = ['gid']

    def ask(self, status):
        if not status.info['exists']:
            return _("'{}' not found in /etc/group").format(self.name)

        return "{} {} → {}\n".format(
            bold(_("GID")),
            status.info['gid'],
            self.attributes['gid'],
        )

    def fix(self, status):
        if not status.info['exists']:
            self.node.run("groupadd {}".format(self.name))

        self.node.run("groupmod -g {gid} {groupname}".format(
            gid=self.attributes['gid'],
            groupname=self.name,
        ))

    def get_status(self):
        # verify content of /etc/group
        grep_result = self.node.run(
            "grep -e '^{}:' /etc/group".format(self.name),
            may_fail=True,
        )
        if grep_result.return_code != 0:
            return ItemStatus(correct=False, info={'exists': False})

        status = ItemStatus(correct=True, info={'exists': True})
        status.info.update(_parse_group_line(grep_result.stdout))

        if status.info['gid'] != self.attributes['gid']:
            status.correct = False

        return status

    @classmethod
    def validate_name(cls, name):
        for char in name:
            if char not in _USERNAME_VALID_CHARACTERS:
                raise BundleError(
                    _("Invalid character in group name '{}': {}").format(name, char)
                )

        if name.endswith("_") or name.endswith("-"):
            raise BundleError(
                _("Group name '{}' must not end in dash or underscore")
            )

        if len(name) > 30:
            raise BundleError(
                _("Group name '{}' is longer than 30 characters")
            )
