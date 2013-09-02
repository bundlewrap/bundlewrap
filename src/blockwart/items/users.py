# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from blockwart.items import Item


class User(Item):
    """
    A user account.
    """
    BUNDLE_ATTRIBUTE_NAME = "users"
    DEPENDS_STATIC = []
    ITEM_ATTRIBUTES = {
        'full_name': "",
        'gid': None,
        'home': None,
        'password': "!",
        'shell': "",
        'uid': None,
    }
    ITEM_TYPE_NAME = "user"
