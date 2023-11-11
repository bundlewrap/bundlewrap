from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def svc_start(node, svcname):
    return node.run("rcctl start {}".format(quote(svcname)), may_fail=True)


def svc_running(node, svcname):
    result = node.run("rcctl check {}".format(quote(svcname)), may_fail=True)
    return "ok" in result.stdout_text


def svc_stop(node, svcname):
    return node.run("rcctl stop {}".format(quote(svcname)), may_fail=True)


def svc_enable(node, svcname):
    return node.run("rcctl set {} status on".format(quote(svcname)), may_fail=True)


def svc_enabled(node, svcname):
    result = node.run("rcctl get {} status".format(quote(svcname)), may_fail=True)
    return result.return_code == 0


def svc_disable(node, svcname):
    return node.run("rcctl set {} status off".format(quote(svcname)), may_fail=True)


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

    @classmethod
    def block_concurrent(cls, node_os, node_os_version):
        # https://github.com/bundlewrap/bundlewrap/issues/554
        return [cls.ITEM_TYPE_NAME]

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
            'stop': {
                'command': "rcctl stop {0}".format(self.name),
                'needed_by': {self.id},
            },
            'stopstart': {
                'command': "rcctl stop {0} && rcctl start {0}".format(self.name),
                'needs': {self.id},
            },
            'restart': {
                'command': "rcctl restart {}".format(self.name),
                'needs': {
                    # make sure we don't restart and stopstart simultaneously
                    f"{self.id}:stopstart",
                    # with only the dep on stopstart, we might still end
                    # up reloading if the service itself is skipped
                    # because the stopstart action has cascade_skip False
                    self.id,
                },
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
