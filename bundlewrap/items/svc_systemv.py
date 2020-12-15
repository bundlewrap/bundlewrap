from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


def svc_start(node, svcname):
    return node.run("/etc/init.d/{} start".format(quote(svcname)), may_fail=True)


def svc_running(node, svcname):
    result = node.run(
        "/etc/init.d/{} status".format(quote(svcname)),
        may_fail=True,
    )
    return result.return_code == 0


def svc_stop(node, svcname):
    return node.run("/etc/init.d/{} stop".format(quote(svcname)), may_fail=True)


class SvcSystemV(Item):
    """
    A service managed by traditional System V init scripts.
    """
    BUNDLE_ATTRIBUTE_NAME = "svc_systemv"
    ITEM_ATTRIBUTES = {
        'running': True,
    }
    ITEM_TYPE_NAME = "svc_systemv"

    def __repr__(self):
        return "<SvcSystemV name:{} running:{}>".format(
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
                'command': "/etc/init.d/{} reload".format(self.name),
                'needs': {
                    # make sure we don't reload and restart simultaneously
                    f"{self.id}:restart",
                    # with only the dep on restart, we might still end
                    # up reloading if the service itself is skipped
                    # because the restart action has cascade_skip False
                    self.id,
                },
            },
            'restart': {
                'command': "/etc/init.d/{} restart".format(self.name),
                'needs': {self.id},
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
