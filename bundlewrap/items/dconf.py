from ast import literal_eval
from json import dumps

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


class DconfSettingsItem(Item):
    """
    `dconf` settings, primarily used by GNOME applications.
    Also known as `gsettings` sometimes.
    """
    BUNDLE_ATTRIBUTE_NAME = 'dconf'
    ITEM_ATTRIBUTES = {
        'value': None,
        'reset': False,
    }
    ITEM_TYPE_NAME = 'dconf'

    def __repr__(self):
        return f'<dconf user:{self.user} path:{self.path}>'

    @property
    def user(self):
        return self.name.split('/', 1)[0]

    @property
    def path(self):
        return '/' + self.name.split('/', 1)[1]

    def _parse_result(self, result):
        stdout = result.stdout.decode('UTF-8').strip()
        if stdout.startswith('uint'):
            stdout = ' '.join(stdout.split(' ')[1:])
        if len(stdout) == 0:
            return None
        elif stdout.isdigit():
            return int(stdout)
        elif stdout == 'true':
            return True
        elif stdout == 'false':
            return False
        else:
            try:
                return literal_eval(stdout)
            except Exception:
                return stdout

    def run(self, command, **kwargs):
        result = self.node.run(
            f'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u {self.user})/bus {command}',
            user=self.user,
            **kwargs,
        )
        self._command_results.append({
            'command': command,
            'result': result,
        })
        return result

    def get_auto_attrs(self, items):
        needs = set()
        after = set()
        for item in items:
            # We need to depend on the user item and the GNOME packages.
            # To increase the chance of the setting being available, we
            # try to run this item after all package installations have
            # succeeded.
            if item.ITEM_TYPE_NAME == 'user' and item.name == self.user:
                needs.add(item.id)
            elif item.ITEM_TYPE_NAME.startswith('pkg_') and item.name.lower().startswith('gnome'):
                needs.add(item.id)
            elif item.ITEM_TYPE_NAME.startswith('pkg_'):
                after.add(item.id)
        return {
            'after': after,
            'needs': needs,
        }

    def cdict(self):
        if self.attributes['reset']:
            return None

        return {
            'value': self.attributes['value'],
        }

    def sdict(self):
        result = self.run(f'dconf read {self.path}', may_fail=True)
        value = self._parse_result(result)

        if value is None:
            return None

        return {
            'value': value,
        }

    def fix(self, status):
        if status.must_be_created or status.keys_to_fix:
            value = dumps(self.attributes['value'])
            if value.isdigit():
                value = f'uint32 {value}'
            self.run("dconf write {path} '{value}'".format(
                path=self.path,
                value=value,
            ))
        elif status.must_be_deleted:
            self.run('dconf reset {self.path}')

    def patch_attributes(self, attributes):
        if isinstance(attributes.get('value', []), set):
            attributes['value'] = sorted(attributes['value'])
        return attributes

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if 'value' not in attributes and not attributes.get('reset', False):
            raise BundleError(_(
                'Item {item_id} in bundle {bundle} has no value set. '
                'Please explicitely set the "reset" attribute if you '
                'wish to reset this setting to the default value.'
            ).format(item_id=item_id, bundle=bundle.name))
        if not isinstance(attributes.get('value', []), (set, list, str, int, bool)):
            raise BundleError(_(
                'Item {item_id} in bundle {bundle} uses invalid type '
                'for its "value" attribute, must be of type str, int, '
                'list, set, bool.'
            ).format(item_id=item_id, bundle=bundle.name))

    @classmethod
    def validate_name(cls, bundle, name):
        if '/' not in name:
            raise BundleError(_(
                'Item {name} in bundle {bundle} has invalid name, must '
                'be in "user/path/to/setting" format.'
            ).format(name=name, bundle=bundle.name))
        user, path = name.split('/', 1)
        if not user or not path:
            raise BundleError(_(
                'Item {name} in bundle {bundle} is missing either '
                'username or path in item name.'
            ).format(name=name, bundle=bundle.name))
