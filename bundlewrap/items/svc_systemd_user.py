from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _, force_text

CMD_TEMPLATE = (
    "sudo -u {user}"
    " XDG_RUNTIME_DIR=/run/user/{uid}"
    " DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{uid}/systemd/private"
    " systemctl --user {action} -- {svcname}"
)


class SvcSystemdUser(Item):
    """
    A service managed by systemd.
    """
    BUNDLE_ATTRIBUTE_NAME = "svc_systemd_user"
    ITEM_ATTRIBUTES = {
        'enabled': True,
        'running': True,
        'user': 'some_username',
    }
    ITEM_TYPE_NAME = "svc_systemd_user"
    REQUIRED_ATTRIBUTES = ['user']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache UID on first access to avoid multiple remote calls
        self._uid = None

    @property
    def uid(self):
        if self._uid is None:
            res = self.node.run(f"id -u {quote(self.attributes['user'])}", may_fail=True)
            if res.return_code != 0:
                # If user doesn't exist yet, we can't get UID.
                # This might happen during initial apply.
                return "0"
            self._uid = res.stdout.decode().strip()
        return self._uid

    def __repr__(self):
        return "<SvcSystemdUser name:{} user:{} enabled:{} running:{}>".format(
            self.name,
            self.attributes['user'],
            self.attributes['enabled'],
            self.attributes['running'],
        )

    @property
    def expected_state(self):
        state = {}

        for option, value in self.attributes.items():
            if value is not None:
                state[option] = value

        return state

    def fix(self, status):
        if 'enabled' in status.keys_to_fix:
            if self.attributes['enabled']:
                self.run_action('enable'),
            else:
                self.run_action('disable'),

        if 'running' in status.keys_to_fix:
            if self.attributes['running']:
                self.run_action('start'),
            else:
                self.run_action('stop'),

    def get_canned_actions(self):
        return {
            'stop': {
                'command': self.command_for_action('stop'),
                'needed_by': {self.id},
            },
            'restart': {
                'command': self.command_for_action('restart'),
                'needs': {self.id},
            },
            'reload': {
                'command': self.command_for_action('reload'),
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

    @property
    def actual_state(self):
        enabled_result = self.run_action('is-enabled')
        return {
            'enabled': enabled_result.return_code == 0 and force_text(
                enabled_result.stdout).strip() != "enabled-runtime",
            'running': self.run_action('status').return_code == 0,
            'user': self.attributes['user'],
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

    def command_for_action(self, action: str):
        return CMD_TEMPLATE.format(
            user=quote(self.attributes['user']),
            uid=self.uid,
            action=action,
            svcname=quote(self.name),
        )

    def run_action(self, action: str):
        return self.node.run(self.command_for_action(action), may_fail=True)
