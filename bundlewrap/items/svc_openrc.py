from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def svc_start(node, svcname):
    return node.run(f"rc-service {quote(svcname)} start", may_fail=True)


def svc_running(node, svcname):
    result = node.run(f"rc-service {quote(svcname)} status", may_fail=True)
    return result.return_code == 0 and "started" in result.stdout_text


def svc_stop(node, svcname):
    return node.run(f"rc-service {quote(svcname)} stop", may_fail=True)


def svc_enable(node, svcname, runlevel):
    return node.run(f"rc-update add {quote(svcname)} {quote(runlevel)}", may_fail=True)


def svc_enabled(node, svcname, runlevel):
    result = node.run(
        f"rc-update show {quote(runlevel)} | grep -w {quote(svcname)}", may_fail=True
    )
    return result.return_code == 0 and svcname in result.stdout_text


def svc_runlevel(node, svcname):
    result = node.run(
        f"rc-update show --all | grep -w {quote(svcname)} | cut -d \\| -f 2",
        may_fail=True,
    )
    return result.stdout_text.strip() if result.return_code == 0 else None


def svc_disable(node, svcname, runlevel):
    return node.run(f"rc-update del {quote(svcname)} {quote(runlevel)}", may_fail=True)


class SvcOpenRC(Item):
    """
    A service managed by OpenRC init scripts.
    """

    BUNDLE_ATTRIBUTE_NAME = "svc_openrc"
    ITEM_ATTRIBUTES = {
        "running": True,
        "enabled": True,
        "runlevel": "default",
    }
    ITEM_TYPE_NAME = "svc_openrc"

    def __repr__(self):
        return "<SvcOpenRC name:{} runlevel:{} enabled:{} running:{}>".format(
            self.name, self.attributes["runlevel"], self.attributes["enabled"], self.attributes["running"],
        )

    def fix(self, status):
        if "enabled" in status.keys_to_fix:
            if self.attributes["enabled"]:
                svc_enable(self.node, self.name, self.attributes["runlevel"])
            else:
                svc_disable(self.node, self.name, self.attributes["runlevel"])

        if "running" in status.keys_to_fix:
            if self.attributes["running"]:
                svc_start(self.node, self.name)
            else:
                svc_stop(self.node, self.name)

        if "runlevel" in status.keys_to_fix:
            if status.sdict.runlevel:
                svc_disable(self.node, self.name, status.sdict.runlevel)
            svc_enable(self.node, self.name, self.attributes["runlevel"])

    def get_canned_actions(self):
        return {
            "stop": {
                "command": f"rc-service {self.name} stop",
                "needed_by": {self.id},
            },
            "restart": {
                "command": f"rc-service {self.name} restart",
                "needs": {self.id},
            },
            "reload": {
                "command": f"rc-service {self.name} reload".format(self.name),
                "needs": {
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
            "enabled": svc_enabled(self.node, self.name, self.attributes["runlevel"]),
            "running": svc_running(self.node, self.name),
            "runlevel": svc_runlevel(self.node, self.name),
        }

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        for attribute in ("enabled", "running"):
            if attributes.get(attribute, None) not in (True, False, None):
                raise BundleError(
                    _(
                        "expected boolean or None for '{attribute}' on {item} in bundle '{bundle}'"
                    ).format(
                        attribute=attribute, bundle=bundle.name, item=item_id,
                    )
                )
