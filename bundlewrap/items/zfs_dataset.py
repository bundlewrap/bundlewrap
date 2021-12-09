from pipes import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _
from bundlewrap.utils import cached_property


class ZFSDataset(Item):
    """
    Creates ZFS datasets and manages their properties.
    """
    BUNDLE_ATTRIBUTE_NAME = "zfs_datasets"
    REJECT_UNKNOWN_ATTRIBUTES = False
    ITEM_TYPE_NAME = "zfs_dataset"
    # for defaults which should be different from 'zfs inherit -S' behaviour
    PROPERTY_DEFAULTS = {
        'mountpoint': 'none',
    }

    def __repr__(self):
        return f"<ZFSDataset name:{self.name} {' '.join(f'{k}:{v}' for k,v in self.__item_properties.items())}>"

    # HELPERS

    def __zfs(self, cmd):
        return self.run(f'zfs {cmd}').stdout.decode('utf-8').strip()

    def __get_property(self, property):
        if (
            # always consider properties with a custom default value as changed
            property in self.PROPERTY_DEFAULTS or
            # properties with a value source other than 'local' are unchanged
            self.__zfs(f'get {property} {self.name} -p -H -o source') == 'local'
        ):
            return self.__zfs(f'get {property} {self.name} -p -H -o value')
        else:
            return None

    @cached_property
    def __item_properties(self):
        # all properties wanted by this item
        return {
            **self.PROPERTY_DEFAULTS,
            **{
                property: value
                    for property, value in self.attributes.items()
                    if value is not None
            },
        }

    @cached_property
    def __changed_property_names(self):
        # names of previously changed properties
        if self.__does_exist():
            return self.__zfs(f'get all {self.name} -p -H -o property -s local').splitlines()
        else:
            return []

    def __create(self):
        properties_string = ' '.join(
            f'-o {property}={quote(value)}'
                for property, value in self.__item_properties.items()
        )
        self.run(f'zfs create {properties_string} {self.name}')

    def __does_exist(self):
        return self.run(f'zfs list {self.name}', may_fail=True).return_code == 0

    def __set_property(self, option, value):
        if value == None:
            self.run(f'zfs inherit -S {quote(option)} {quote(self.name)}')
        else:
            self.run(f'zfs set {quote(option)}={quote(value)} {quote(self.name)}')

    # ITEM

    def sdict(self):
        if self.__does_exist():
            return {
                # all relevant properties with their current values
                **{
                    property: self.__get_property(property)
                        for property in {
                            *self.__item_properties,
                            *self.__changed_property_names,
                        }
                },
                # special readonly property 'mounted'
                'mounted': self.__zfs(f'get mounted {self.name} -p -H -o value')
            }
        else:
            return None

    def fix(self, status):
        if status.must_be_created:
            self.__create()
        else:
            for property in status.keys_to_fix:
                if property != 'mounted':
                    self.__set_property(property, status.cdict[property])
            # mount after setting mountpoint property
            if status.cdict['mounted'] != self.__zfs(f'get mounted {self.name} -p -H -o value'):
                mount = 'mount' if status.cdict['mounted'] == 'yes' else 'unmount'
                self.run(f'zfs {mount} {quote(self.name)}')

    def cdict(self):
        return {
            # previously changed properties with their default values
            **{
                property: self.PROPERTY_DEFAULTS.get(property)
                    for property in self.__changed_property_names
            },
            # item properties with their wanted values
            **self.__item_properties,
            # special readonly property 'mounted'
            'mounted': 'no' if self.__item_properties.get('mountpoint') == 'none' else 'yes',
        }

    # DEPENDENCIES

    def get_auto_attrs(self, items):
        pool = self.name.split("/")[0]
        pool_item_found = False
        parent_dataset = '/'.join(self.name.split('/')[0:-1])
        needs = set()

        for item in items:
            if item.ITEM_TYPE_NAME == "zfs_pool" and item.name == pool:
                # add dependency to the pool this dataset resides on
                pool_item_found = True
                needs.add(f'zfs_pool:{pool}')
            elif (
                item.ITEM_TYPE_NAME == "zfs_dataset" and
                item.name == parent_dataset
            ):
                # add dependency to parent dataset
                needs.add(item.id)
            elif self.__item_properties.get('mountpoint'):
                parent_directory = '/'.join(self.__item_properties.get('mountpoint', '').split('/')[0:-1])
                if (
                    item.ITEM_TYPE_NAME == "zfs_dataset" and
                    item.attributes.get('mountpoint') == parent_directory or
                    item.ITEM_TYPE_NAME == "directory" and
                    item.name == parent_directory
                ):
                    # add dependency to parent mountpoint or directory
                    needs.add(item.id)

        if not pool_item_found:
            raise BundleError(_(
                f'ZFS dataset {self.name} resides on pool {pool} but item '
                f'zfs_pool:{pool} does not exist'
            ))

        return {'needs': needs}
