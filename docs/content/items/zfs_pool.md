# ZFS pools

Manages ZFS pools.

    zfs_pools = {
        "tank": {
            "when_creating": {
                "config": [
                    {
                        "type": "mirror",
                        "devices": {
                            "/dev/sda",
                            "/dev/sdb",
                        },
                    },
                ],
                "ashift": 12,
            },
            "autoexpand": False,
            "autoreplace": False,
            "autotrim": True,
        },
    }

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## config

A list of dicts. This allows you to create arbitrary pool configurations.
Each dict must include a `devices` key, which must contain atleast one
device to use. `type` is optional, if set, it must be one of these types:

* `mirror` - creates a mirrored vdev (like RAID1)
* `raidz` - creates a raidz vdev (like RAID5)
* `raidz2` - creates a raidz2 vdev (like RAID6)
* `raidz3` - creates a raidz3 vdev
* `log` - creates a ZIL vdev
* `cache` - creates a L2ARC vdev

When creating a `log` vdev, you may only use one or two devices. BundleWrap
will automatically create a `log mirror` if you specify two devices for your
`log` vdev.

<hr>

## ashift

Sets the `ashift` attribute for a to-be-created pool. `ashift` gets
ignored if the requested pool already exists.

<hr>

## autoexpand, autoreplace, and autotrim

Sets the corresponding zpool options `autoexpand`, `autoreplace` and
`autotrim`.
