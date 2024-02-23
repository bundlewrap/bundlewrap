from collections import Counter
from shlex import quote

from bundlewrap.exceptions import BundleError
from bundlewrap.items import Item
from bundlewrap.utils.text import mark_for_translation as _


class ZFSPool(Item):
    """
    Creates ZFS pools.
    """
    BUNDLE_ATTRIBUTE_NAME = "zfs_pools"
    ITEM_ATTRIBUTES = {
        'autoexpand': None,
        'autoreplace': None,
        'autotrim': None,
    }
    WHEN_CREATING_ATTRIBUTES = {
        'ashift': None,
        'config': None,
    }
    ITEM_TYPE_NAME = "zfs_pool"

    def __repr__(self):
        return "<ZFSPool name:{} autoexpand:{} autoreplace:{} autotrim:{} ashift:{} config:{}>".format(
            self.name,
            self.attributes['autoexpand'],
            self.attributes['autoreplace'],
            self.attributes['autotrim'],
            self.when_creating['ashift'],
            self.when_creating['config'],
        )

    def cdict(self):
        ret = {}
        for i in self.attributes:
            if self.attributes.get(i) is not None:
                ret[i] = self.attributes[i]
        return ret

    @property
    def devices_used(self):
        devices = set()
        for option in self.when_creating['config']:
            for device in option['devices']:
                devices.add(device)
        return sorted(devices)

    def fix(self, status):
        if status.must_be_created:
            cmdline = []
            for option in self.when_creating['config']:
                if option.get('type'):
                    cmdline.append(option['type'])
                    if option['type'] == 'log' and len(option['devices']) > 1:
                        cmdline.append('mirror')

                for device in sorted(option['devices']):
                    res = self.run("lsblk -rndo fstype {}".format(quote(device)))
                    detected = res.stdout.decode('UTF-8').strip()
                    if detected != "":
                        raise BundleError(_(
                            "Node {}, ZFSPool {}: Device {} to be used for ZFS, "
                            "but it is not empty! Has '{}'."
                        ).format(self.node.name, self.name, device, detected))

                    cmdline.append(quote(device))

            options = set()
            if self.when_creating['ashift']:
                options.add('-o ashift={}'.format(self.when_creating['ashift']))

            for opt, value in status.cdict.items():
                state_str = 'on' if value else 'off'
                options.add('-o {}={}'.format(opt, state_str))

            self.run('zpool create {} {} {}'.format(
                ' '.join(sorted(options)),
                quote(self.name),
                ' '.join(cmdline),
            ))
        elif status.keys_to_fix:
            for attr in status.keys_to_fix:
                state_str = 'on' if status.cdict[attr] else 'off'
                self.run('zpool set {}={} {}'.format(attr, state_str, quote(self.name)))

    def sdict(self):
        status_result = self.run('zpool list {}'.format(quote(self.name)), may_fail=True)
        if status_result.return_code != 0:
            return None

        pool_status = {}
        for line in self.run(
            'zpool get all -H -o all {}'.format(quote(self.name)),
            may_fail=True,
        ).stdout.decode().splitlines():
            try:
                pname, prop, value, source = line.split()
                pool_status[prop.strip()] = value.strip()
            except (IndexError, ValueError):
                continue

        sdict = {}
        for attr in self.attributes:
            sdict[attr] = (pool_status.get(attr) == 'on')
        return sdict

    def test(self):
        duplicate_devices = [
            item for item, count in Counter(self.devices_used).items() if count > 1
        ]
        if duplicate_devices:
            raise BundleError(_(
                "{item} on node {node} uses {devices} more than once as an underlying device"
            ).format(
                item=self.id,
                node=self.node.name,
                devices=_(" and ").join(duplicate_devices),
            ))

        # Have a look at all other ZFS pools on this node and check if
        # multiple pools try to use the same device.
        for item in self.node.items:
            if (
                item.ITEM_TYPE_NAME == "zfs_pool" and
                item.name != self.name and
                set(item.devices_used).intersection(set(self.devices_used))
            ):
                raise BundleError(_(
                    "Both the ZFS pools {self} and {other} on node {node} "
                    "try to use {devices} as the underlying storage device"
                ).format(
                    self=self.name,
                    other=item.name,
                    node=self.node.name,
                    devices=_(" and ").join(
                        set(item.devices_used).intersection(set(self.devices_used)),
                    ),
                ))

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if 'config' not in attributes.get('when_creating', {}):
            raise BundleError(_(
                "{item} on node {node}: required option 'config' missing"
            ).format(
                item=item_id,
                node=bundle.node.name,
            ))
        elif not isinstance(attributes['when_creating']['config'], list):
            raise BundleError(_(
                "{item} on node {node}: option 'config' must be a list"
            ).format(
                item=item_id,
                node=bundle.node.name,
            ))

        for config in attributes['when_creating']['config']:
            if config.get('type', None) not in {
                None,
                'mirror',
                'raidz',
                'raidz2',
                'raidz3',
                'cache',
                'log',
            }:
                raise BundleError(_(
                    "{item} on node {node} has invalid type '{type}', "
                    "must be one of (unset), 'mirror', 'raidz', 'raidz2', "
                    "'raidz3', 'cache', 'log'"
                ).format(
                    item=item_id,
                    node=bundle.node.name,
                    type=config['type'],
                ))

            if not config.get('devices', set()):
                raise BundleError(_(
                    "{item} on node {node} uses no devices!"
                ).format(
                    item=item_id,
                    node=bundle.node.name,
                ))

            if (
                config.get('type') == 'log' and
                len(config['devices']) not in (1, 2)
            ):
                raise BundleError(_(
                    "{item} on node {node} type 'log' must use exactly "
                    "one or two devices"
                ).format(
                    item=item_id,
                    node=bundle.node.name,
                ))
