# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def svc_start(node, svcname):
    return node.run("/etc/rc.d/{} start".format(quote(svcname)))


def svc_running(node, svcname):
    result = node.run("/etc/rc.d/{} check".format(quote(svcname)), may_fail=True)
    return "ok" in result.stdout_text


def svc_stop(node, svcname):
    return node.run("/etc/rc.d/{} stop".format(quote(svcname)))


def svc_enable(node, svcname):
    return node.run("rcctl set {} status on".format(quote(svcname)))


def svc_enabled(node, svcname):
    result = node.run(
        "rcctl ls on | grep '^{}$'".format(svcname),
        may_fail=True,
    )
    return result.return_code == 0


def svc_disable(node, svcname):
    return node.run("rcctl set {} status off".format(quote(svcname)))


class SvcOpenBSD(Item):
    """
    A service managed by OpenBSD rc.d.
    """
    BUNDLE_ATTRIBUTE_NAME = "svc_openbsd"
    ITEM_ATTRIBUTES = {
        'running': True,
        'enabled': True
    }
    ITEM_TYPE_NAME = "svc_openbsd"

    def __repr__(self):
        return "<SvcOpenBSD name:{} running:{} enabled:{}>".format(
            self.name,
            self.attributes['running'],
            self.attributes['enabled'],
        )

    def fix(self, status):
        if 'enabled' in status.keys_to_fix:
            if self.attributes['enabled'] is False:
                svc_disable(self.node, self.name)
            else:
                svc_enable(self.node, self.name)

        if self.attributes['running'] is False:
            svc_stop(self.node, self.name)
        else:
            svc_start(self.node, self.name)

    def get_canned_actions(self):
        return {
            'restart': {
                'command': "/etc/rc.d/{} restart".format(self.name),
                'needs': [self.id],
            },
            'stopstart': {
                'command': "/etc/rc.d/{0} stop && /etc/rc.d/{0} start".format(self.name),
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
        if not isinstance(attributes.get('running', True), bool):
            raise BundleError(_(
                "expected boolean for 'running' on {item} in bundle '{bundle}'"
            ).format(
                bundle=bundle.name,
                item=item_id,
            ))
