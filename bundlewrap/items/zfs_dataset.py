from shlex import quote

from bundlewrap.items import Item


class ZFSDataset(Item):
    """
    Creates ZFS datasets and manages their options.
    """
    BUNDLE_ATTRIBUTE_NAME = "zfs_datasets"
    REJECT_UNKNOWN_ATTRIBUTES = False
    ITEM_TYPE_NAME = "zfs_dataset"

    def __repr__(self):
        return f"<ZFSDataset name:{self.name} {' '.join(f'{k}:{v}' for k,v in self.attributes.items())}>"

    def __create(self, path, options):
        option_list = []
        for option, value in sorted(options.items()):
            # We must exclude the 'mounted' property here because it's a
            # read-only "informational" property.
            if option != 'mounted' and value is not None:
                option_list.append("-o {}={}".format(quote(option), quote(value)))
        option_args = " ".join(option_list)

        self.run(
            "zfs create {} {}".format(
                option_args,
                quote(path),
            ),
            may_fail=True,
        )

        if options['mounted'] == 'no':
            self.__set_option(path, 'mounted', 'no')

    def __does_exist(self, path):
        status_result = self.run(
            "zfs list {}".format(quote(path)),
            may_fail=True,
        )
        return status_result.return_code == 0

    def __get_option(self, path, option):
        cmd = "zfs get -Hp -o value {} {}".format(quote(option), quote(path))
        # We always expect this to succeed since we don't call this function
        # if we have already established that the dataset does not exist.
        status_result = self.run(cmd)
        return status_result.stdout.decode('utf-8').strip()

    def __set_option(self, path, option, value):
        if option == 'mounted':
            # 'mounted' is a read-only property that can not be altered by
            # 'set'. We need to call 'zfs mount tank/foo'.
            self.run(
                "zfs {} {}".format(
                    "mount" if value == 'yes' else "unmount",
                    quote(path),
                ),
                may_fail=True,
            )
        else:
            self.run(
                "zfs set {}={} {}".format(
                    quote(option),
                    quote(value),
                    quote(path),
                ),
                may_fail=True,
            )

    def cdict(self):
        cdict = {}
        for option, value in self.attributes.items():
            if option == 'mountpoint' and value is None:
                value = "none"
            if value is not None:
                cdict[option] = value
        cdict['mounted'] = 'no' if cdict.get('mountpoint') in (None, "none") else 'yes'
        return cdict

    def fix(self, status):
        if status.must_be_created:
            self.__create(self.name, status.cdict)
        else:
            for option in status.keys_to_fix:
                self.__set_option(self.name, option, status.cdict[option])

    def get_auto_attrs(self, items):
        pool = self.name.split("/")[0]
        pool_item = "zfs_pool:{}".format(pool)
        needs = set()

        for item in items:
            if item.ITEM_TYPE_NAME == "zfs_pool" and item.name == pool:
                # Add dependency to the pool this dataset resides on.
                needs.add(pool_item)
            elif (
                item.ITEM_TYPE_NAME == "zfs_dataset" and
                self.name != item.name
            ):
                # Find all other datasets that are parents of this
                # dataset.
                # XXX Could be optimized by finding the "largest"
                # parent only.
                if self.name.startswith(item.name + "/"):
                    needs.add(item.id)
                elif (
                    self.attributes.get('mountpoint')
                    and item.attributes.get('mountpoint')
                    and self.attributes['mountpoint'] != item.attributes['mountpoint']
                    and self.attributes['mountpoint'].startswith(item.attributes['mountpoint'])
                ):
                    needs.add(item.id)

        return {'needs': needs}

    def sdict(self):
        if not self.__does_exist(self.name):
            return None

        sdict = {}
        for option in self.attributes:
            sdict[option] = self.__get_option(self.name, option)
        sdict['mounted'] = self.__get_option(self.name, 'mounted')
        return sdict
