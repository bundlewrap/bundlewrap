# ZFS datasets

Manages ZFS datasets.

    zfs_datasets = {
        "tank/mydataset": {
            "acltype": "posixacl",
            "atime": "on",
            "compression": "on",
            "dedup": "off",
            "mountpoint": "/mnt/mydataset",
            "quota": "1G",
            "recordsize": "131072",
        },
    }

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## mountpoint

Controls where the dataset should be mounted. If you set this to `None`,
bundlewrap will also automatically unmount the dataset for you. The dataset
will get mounted if you specify a mountpoint.

<hr>

## acltype, atime, compression, dedup, quota, and recordsize

Sets the corresponding dataset options `acltype`, `atime`, `compression`,
`dedup`, `quota` and `recordsize`.
