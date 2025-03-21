from contextlib import suppress

from bundlewrap.exceptions import BundleError
from bundlewrap.items import BUILTIN_ITEM_ATTRIBUTES, Item
from bundlewrap.utils.text import mark_for_translation as _

UNMANAGED_SUBITEMS_DESC = _("unmanaged subitems")


class RouterOS(Item):
    """
    RouterOS configuration.
    """
    BUNDLE_ATTRIBUTE_NAME = "routeros"
    ITEM_ATTRIBUTES = {
        'delete': False,
        'purge': False,
    }
    ITEM_TYPE_NAME = "routeros"
    REJECT_UNKNOWN_ATTRIBUTES = False

    @classmethod
    def block_concurrent(cls, node_os, node_os_version):
        return [cls.ITEM_TYPE_NAME]

    def __repr__(self):
        return f"<RouterOS {self.name} delete:{self.attributes['delete']} purge:{bool(self.attributes['purge'])}>"

    def cdict(self):
        if self.attributes['delete']:
            return None

        if self.attributes['purge']:
            # purge operates on lists of items only which we can't operate on otherwise
            return {
                'subitems_to_purge': set()
            }

        cdict = self.attributes.copy()
        if '_comment' in cdict:  # work around 'comment' being a builtin attribute
            cdict['comment'] = cdict['_comment']
            del cdict['_comment']

        del cdict['delete']
        del cdict['purge']
        return cdict

    def get_basename(self, name):
        return name.split("?", 1)[0]

    @property
    def basename(self):
        return self.get_basename(self.name)

    def get_identifier(self, name):
        return name.split("?", 1)[1]

    @property
    def identifier(self):
        return self.get_identifier(self.name)

    def fix(self, status):
        if status.sdict:
            for subitem_id, subitem_name in status.sdict.get('subitems_to_purge', set()):
                self._remove(self.basename, subitem_id)

        if status.must_be_created:
            cdict = status.cdict.copy()
            with suppress(KeyError):
                del cdict['subitems_to_purge']
            self._add(self.basename, cdict)
        elif status.must_be_deleted:
            self._remove(self.basename, status.sdict['.id'])
        else:
            values_to_fix = {
                key: status.cdict[key]
                for key in status.keys_to_fix
                if key not in ('subitems_to_purge',)
            }
            if values_to_fix:
                self._set(
                    self.basename,
                    status.sdict.get('.id'),
                    values_to_fix
                )

    def sdict(self):
        if self.attributes['purge']:
            # purge operates on lists of items only which we can't operate on otherwise
            return {
                'subitems_to_purge': self._get_subitems_to_purge()
            }

        result = self._get(self.name)
        if result:
            # API doesn't return comment at all if emtpy
            result.setdefault('comment', '')
            # undo automatic type conversion in librouteros
            for key, value in tuple(result.items()):
                if value is True:
                    result[key] = "yes"
                elif value is False:
                    result[key] = "no"
                elif isinstance(value, int):
                    result[key] = str(value)
        return result

    def display_on_create(self, cdict):
        for key in tuple(cdict.keys()):
            if cdict[key].count(",") > 2:
                cdict[key] = cdict[key].split(",")
        return cdict

    def display_dicts(self, cdict, sdict, keys):
        if 'subitems_to_purge' in keys:
            keys.remove('subitems_to_purge')
            keys.append(UNMANAGED_SUBITEMS_DESC)
            cdict[UNMANAGED_SUBITEMS_DESC] = sorted([name for id, name in cdict['subitems_to_purge']])
            sdict[UNMANAGED_SUBITEMS_DESC] = sorted([name for id, name in sdict['subitems_to_purge']])
            del cdict['subitems_to_purge']
            del sdict['subitems_to_purge']

        for key in keys:
            if cdict[key].count(",") > 2 or sdict[key].count(",") > 2:
                cdict[key] = cdict[key].split(",")
                sdict[key] = sdict[key].split(",")
        return (cdict, sdict, keys)

    def display_on_delete(self, sdict):
        with suppress(KeyError):
            del sdict['subitems_to_purge']
            del sdict[".id"]
        for key in tuple(sdict.keys()):
            if sdict[key].count(",") > 2:
                sdict[key] = sdict[key].split(",")
        return sdict

    def patch_attributes(self, attributes):
        for key in tuple(attributes.keys()):
            if key in BUILTIN_ITEM_ATTRIBUTES:
                continue
            value = attributes[key]
            # We need to stringify bools and ints because librouteros
            # will convert them anyway and we must have a consistent
            # representation for the purpose of diffing.
            if value is True:
                attributes[key] = "yes"
            elif value is False:
                attributes[key] = "no"
            elif isinstance(value, int):
                attributes[key] = str(value)
            elif isinstance(value, set):
                attributes[key] = ",".join(sorted(value))
            elif isinstance(value, (tuple, list)):
                attributes[key] = ",".join(value)
        return attributes

    def run_routeros(self, *command):
        result = self.node.run_routeros(*command)
        self._command_results.append({
            'command': repr(command),
            'result': result,
        })
        return result

    def parse_identifier(self, identifier):
        kwargs = {}
        for identifier_component in identifier.split("&"):
            identifier_key, identifier_value = identifier_component.split("=", 1)
            kwargs[identifier_key] = identifier_value

        return kwargs

    def _add(self, command, kwargs):
        kwargs |= self.parse_identifier(self.identifier)
        command += "/add"
        arguments = [f"={key}={value}" for key, value in kwargs.items()]
        self.run_routeros(command, *arguments)

    def _list(self, command):
        if "?" in command:
            command, query = command.split("?", 1)
            query = query.split("&")
            query = ["?=" + condition for condition in query]
            query.append("?#&")  # AND all conditions
            return self.run_routeros(command + "/print", *query).raw
        else:
            return self.run_routeros(command + "/print").raw

    def _get(self, command):
        result = self._list(command)
        if not result:
            return None
        elif len(result) == 1:
            return result[0]
        else:
            raise BundleError(_(
                "{item} on {node} returned ambiguous data from API: {result}"
            ).format(
                item=self.id,
                node=self.node.name,
                result=repr(result),
            ))

    def _set(self, command, api_id, values_to_fix):
        command += "/set"
        kvpairs = [
            f"={key}={value}"
            for key, value in sorted(values_to_fix.items())
        ]
        if api_id is None:
            self.run_routeros(command, *kvpairs)
        else:
            self.run_routeros(command, f"=.id={api_id}", *kvpairs)

    def _remove(self, command, api_id):
        self.run_routeros(command + "/remove", f"=.id={api_id}")

    def _get_subitems_to_purge(self):
        raw_items = self._list(self.basename)
        if not raw_items:
            return set()

        purge_cfg = self.attributes.get('purge', {})
        if not isinstance(purge_cfg, dict):
            purge_cfg = {}

        id_by = purge_cfg.get('id-by', 'name')
        keep = purge_cfg.get('keep', {})

        existing_items = {
            raw_item['.id']: str(raw_item[id_by])
            for raw_item in raw_items
            if not self._subitem_matches_filter(raw_item, keep)
        }

        desired_items = [
            self.parse_identifier(self.get_identifier(item.id))[id_by]
            for item in self.node.items
            if item.id.startswith(f'routeros:{self.basename}?{id_by}=')
        ]

        items_to_delete = set(
            (existing_item_id, existing_item_name)
            for existing_item_id, existing_item_name in existing_items.items()
            if existing_item_name not in desired_items
        )

        return items_to_delete

    def _subitem_matches_filter(self, subitem, filter):
        for k, v in filter.items():
            if subitem.get(k, None) == v:
                return True

        return False
