from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import force_text, mark_for_translation as _


def svc_start(node, svcname):
    return node.run("systemctl start -- {}".format(quote(svcname)), may_fail=True)


def svc_running(node, svcname):
    result = node.run(
        "systemctl status -- {}".format(quote(svcname)),
        may_fail=True,
    )
    return result.return_code == 0


def svc_stop(node, svcname):
    return node.run("systemctl stop -- {}".format(quote(svcname)), may_fail=True)


def svc_enable(node, svcname):
    return node.run("systemctl enable -- {}".format(quote(svcname)), may_fail=True)


def svc_enabled(node, svcname):
    result = node.run(
        "systemctl is-enabled -- {}".format(quote(svcname)),
        may_fail=True,
    )
    return (
        result.return_code == 0 and
        force_text(result.stdout).strip() != "runtime-enabled"
    )


def svc_disable(node, svcname):
    return node.run("systemctl disable -- {}".format(quote(svcname)), may_fail=True)

def svc_mask(node, svcname):
    return node.run("systemctl mask -- {}".format(quote(svcname)), may_fail=True)

def svc_masked(node, svcname):
    result = node.run(
        "systemctl is-enabled -- {}".format(quote(svcname)),
        may_fail=True,
    )
    return (
        result.return_code == 1 and
        force_text(result.stdout).strip() == "masked"
    )

def svc_unmask(node, svcname):
    return node.run("systemctl unmask -- {}".format(quote(svcname)), may_fail=True)


class SvcSystemd(Item):
    """
    A service managed by systemd.
    """
    BUNDLE_ATTRIBUTE_NAME = "svc_systemd"
    ITEM_ATTRIBUTES = {
        'enabled': True,
        'running': True,
        'masked': False,
    }
    ITEM_TYPE_NAME = "svc_systemd"

    def __repr__(self):
        return "<SvcSystemd name:{} enabled:{} running:{} masked:{}>".format(
            self.name,
            self.attributes['enabled'],
            self.attributes['running'],
            self.attributes['masked'],
        )

    def cdict(self):
        cdict = {}
        for option, value in self.attributes.items():
            if value is not None:
                cdict[option] = value
        return cdict

    def fix(self, status):
        if 'masked' in status.keys_to_fix:
            if self.attributes['masked']:
                svc_mask(self.node, self.name)
            else:
                svc_unmask(self.node, self.name)

        if 'enabled' in status.keys_to_fix:
            if self.attributes['enabled']:
                svc_enable(self.node, self.name)
            else:
                svc_disable(self.node, self.name)

        if 'running' in status.keys_to_fix:
            if self.attributes['running']:
                svc_start(self.node, self.name)
            else:
                svc_stop(self.node, self.name)

    def get_canned_actions(self):
        return {
            'stop': {
                'command': "systemctl stop -- {}".format(self.name),
                'needed_by': {self.id},
            },
            'restart': {
                'command': "systemctl restart -- {}".format(self.name),
                'needs': {self.id},
            },
            'reload': {
                'command': "systemctl reload -- {}".format(self.name),
                'needs': {
                    # make sure we don't reload and restart simultaneously
                    f"{self.id}:restart",
                    # with only the dep on restart, we might still end
                    # up reloading if the service itself is skipped
                    # because the restart action has cascade_skip False
                    self.id,
                },
            },
        }

    def sdict(self):
        return {
            'enabled': svc_enabled(self.node, self.name),
            'running': svc_running(self.node, self.name),
            'masked': svc_masked(self.node, self.name),
        }

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        for attribute in ('enabled', 'running'):
            if attributes.get(attribute, None) not in (True, False, None):
                raise BundleError(_(
                    "expected boolean or None for '{attribute}' on {item} in bundle '{bundle}'"
                ).format(
                    attribute=attribute,
                    bundle=bundle.name,
                    item=item_id,
                ))
