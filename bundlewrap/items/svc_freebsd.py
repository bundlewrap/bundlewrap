from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def svc_start(node, svcname):
    return node.run("/usr/sbin/service {} start".format(quote(svcname)), may_fail=True)


def svc_running(node, svcname):
    result = node.run("/usr/sbin/service {} status".format(quote(svcname)), may_fail=True)
    return "is running as" in result.stdout_text


def svc_stop(node, svcname):
    return node.run("/usr/sbin/service {} stop".format(quote(svcname)), may_fail=True)


def svc_enable(node, svcname):
    return node.run("/usr/sbin/service {} enable".format(quote(svcname)), may_fail=True)


def svc_enabled(node, svcname):
    result = node.run("/usr/sbin/service {} enabled".format(svcname), may_fail=True,)
    return result.return_code == 0


def svc_disable(node, svcname):
    return node.run("/usr/sbin/service {} disable".format(quote(svcname)), may_fail=True)


class SvcFreeBSD(Item):
    """
    A service managed by FreeBSD.
    """
    BUNDLE_ATTRIBUTE_NAME = "svc_freebsd"
    ITEM_ATTRIBUTES = {
        'running': True,
        'enabled': True
    }
    ITEM_TYPE_NAME = "svc_freebsd"

    @classmethod
    def block_concurrent(cls, node_os, node_os_version):
        # SH: This should apply here as well
        # https://github.com/bundlewrap/bundlewrap/issues/554
        return [cls.ITEM_TYPE_NAME]

    def __repr__(self):
        return "<SvcFreeBSD name:{} running:{} enabled:{}>".format(
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
                'command': "/usr/sbin/service {0} stop".format(self.name),
                'needed_by': {self.id},
            },
            'stopstart': {
                'command': "/usr/sbin/service {0} stop && /usr/sbin/service {0} start".format(self.name),
                'needs': {self.id},
            },
            'restart': {
                'command': "/usr/sbin/service {} restart".format(self.name),
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
