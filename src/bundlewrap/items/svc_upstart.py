# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def svc_start(node, svcname):
    return node.run("initctl start --no-wait -- {}".format(quote(svcname)))


def svc_running(node, svcname):
    result = node.run("initctl status -- {}".format(quote(svcname)))
    return " start/" in result.stdout_text


def svc_stop(node, svcname):
    return node.run("initctl stop --no-wait -- {}".format(quote(svcname)))


class SvcUpstart(Item):
    """
    A service managed by Upstart.
    """
    BUNDLE_ATTRIBUTE_NAME = "svc_upstart"
    ITEM_ATTRIBUTES = {
        'running': True,
    }
    ITEM_TYPE_NAME = "svc_upstart"

    def __repr__(self):
        return "<SvcUpstart name:{} running:{}>".format(
            self.name,
            self.attributes['running'],
        )

    def fix(self, status):
        if self.attributes['running'] is False:
            svc_stop(self.node, self.name)
        else:
            svc_start(self.node, self.name)

    def get_canned_actions(self):
        return {
            'reload': {
                'command': "reload {}".format(self.name),
                'needs': [self.id],
            },
            'restart': {
                'command': "restart {}".format(self.name),
                'needs': [self.id],
            },
            'stopstart': {
                'command': "stop {0} && start {0}".format(self.name),
                'needs': [self.id],
            },
        }

    def sdict(self):
        return {'running': svc_running(self.node, self.name)}

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if not isinstance(attributes.get('running', True), bool):
            raise BundleError(_(
                "expected boolean for 'running' on {item} in bundle '{bundle}'"
            ).format(
                bundle=bundle.name,
                item=item_id,
            ))
