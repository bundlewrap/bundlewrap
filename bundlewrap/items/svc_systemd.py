# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def svc_start(node, svcname):
    return node.run("systemctl start -- {}".format(quote(svcname)))


def svc_running(node, svcname):
    result = node.run(
        "systemctl status -- {}".format(quote(svcname)),
        may_fail=True,
    )
    return result.return_code == 0


def svc_stop(node, svcname):
    return node.run("systemctl stop -- {}".format(quote(svcname)))


def svc_enable(node, svcname):
    return node.run("systemctl enable -- {}".format(quote(svcname)))


def svc_enabled(node, svcname):
    result = node.run(
        "systemctl is-enabled -- {}".format(quote(svcname)),
        may_fail=True,
    )
    return result.return_code == 0


def svc_disable(node, svcname):
    return node.run("systemctl disable -- {}".format(quote(svcname)))


class SvcSystemd(Item):
    """
    A service managed by systemd.
    """
    BUNDLE_ATTRIBUTE_NAME = "svc_systemd"
    ITEM_ATTRIBUTES = {
        'enabled': None,
        'running': True,
    }
    ITEM_TYPE_NAME = "svc_systemd"

    def __repr__(self):
        return "<SvcSystemd name:{} enabled:{} running:{}>".format(
            self.name,
            self.attributes['enabled'],
            self.attributes['running'],
        )

    # Note for bw 3.0: We're planning to make "True" the default value
    # for "enabled". Once that's done, we can remove this custom cdict.
    def cdict(self):
        cdict = self.attributes.copy()
        if 'enabled' in cdict and cdict['enabled'] is None:
            del cdict['enabled']
        return cdict

    def fix(self, status):
        if 'enabled' in status.keys_to_fix:
            if self.attributes['enabled'] is False:
                svc_disable(self.node, self.name)
            else:
                svc_enable(self.node, self.name)

        if 'running' in status.keys_to_fix:
            if self.attributes['running'] is False:
                svc_stop(self.node, self.name)
            else:
                svc_start(self.node, self.name)

    def get_canned_actions(self):
        return {
            'reload': {
                'command': "systemctl reload -- {}".format(self.name),
                'needs': [self.id],
            },
            'restart': {
                'command': "systemctl restart -- {}".format(self.name),
                'needs': [self.id],
            },
        }

    def sdict(self):
        return {
            'enabled': svc_enabled(self.node, self.name),
            'running': svc_running(self.node, self.name),
        }

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        for attribute in ('enabled', 'running'):
            if not isinstance(attributes.get(attribute, True), bool):
                raise BundleError(_(
                    "expected boolean for '{attribute}' on {item} in bundle '{bundle}'"
                ).format(
                    attribute=attribute,
                    bundle=bundle.name,
                    item=item_id,
                ))
