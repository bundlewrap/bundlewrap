# RouterOS items

Manages RouterOS configuration through the API (port 8728). You can address every configuration exposed by the API by
constructing the item name and attributes accordingly. If you haven't already, familiarize yourself with the CLI over
SSH first. Use it as a reference when composing items in your bundles. <strong>Don't forget to set the <code>os</code>
attribute of your node to <code>routeros</code> and also set the <code>username</code> and <code>password</code>
attributes.</strong>

    routeros = {
        "/ip/dns": {
            "servers": "8.8.8.8",
        },
        "/interface/vlan?name=vlan6": {
            "vlan-id": "6",
            "interface": "bridge",
            "needs": {
                "routeros:/interface/bridge?name=bridge",
            },
        },
        "/interface/vlan?name=vlan7": {
            "delete": True,
        },
        "/interface/vlan": {
            "purge": {
                "id-by": "name",
            },
        },
        "/interface/bridge?name=bridge": {},
        "/interface/bridge/port?interface=ether8": {
            "bridge": "bridge",
            "needs": {
                "routeros:/interface/bridge?name=bridge",
            },
        },
        "/interface/bridge/port": {
            "purge": {
                "id-by": "interface",
            },
        },
        "/interface/bridge/vlan?vlan-ids=6": {
            "bridge": "bridge",
            "needs": {
                "routeros:/interface/bridge?name=bridge",
            },
            "tagged": {
                "ether10",
                "ether11",
                "ether12",
            },
            "untagged": {
                "ether13",
                "ether14",
                "ether15",
            },
        },
        "/interface/bridge/vlan": {
            "purge": {
                "id-by": "vlan-ids",
                "keep": {
                    "dynamic": True,
                },
            },
        },
        "/interface/bonding?name=LAG1": {
            "mode": "802.3ad",
            "slaves": ["ether2", "ether3"],
            "transmit-hash-policy": "layer-3-and-4",
        },
        "/interface/bonding": {
            "purge": {
                "id-by": "name",
            },
        },
        "/system/logging?action=remote&topics=critical": {},
    }

Note that when configuring an item from a list of things, item names have two parts, separated by a `?` character. The
first part determines which kind of item is addressed, the second part is a simple `key=value` query that MUST return
exactly one entry. If a list has no single "primary key" (such as `/system/logging`), use `&` to add more conditions.

For lists of things, the purge option can be used to instruct BundleWrap to remove items it doesn't know about (see the
Purging section).

For example `/interface/vlan` addresses all VLAN interfaces (a list of things) and can be configured to purge unmanaged
VLANs, whereas `/interface/vlan?name=vlan7` configures a specific VLAN.

# Purging

For any lists of things (VLAN interfaces, bonds) the purge option can be enabled:

```
        "/interface/vlan?name=vlan6": {
            "vlan-id": "6",
            "interface": "bridge",
            "needs": {
                "routeros:/interface/bridge?name=bridge",
            },
        },
        "/interface/vlan": {
            "purge": {
                "id-by": "name",
            },
        },
```

The `id-by` option tells BundleWrap to identify configured items by the specified key. In the above example, BundleWrap
searches for all items with item ids starting wih `/interface/vlan` that contain a `name` key. It
finds `/interface/vlan?name=vlan6` and assumes that only one VLAN should be configured and it should have a `name`
of `vlan6`. It will then delete any VLANs on the node not matching this selection.

For different items, different selection keys are useful. For example for bridge ports, the `interface` key is often
used:

```
        "/interface/bridge/port?interface=ether8": {
            "bridge": "bridge",
            "needs": {
                "routeros:/interface/bridge?name=bridge",
            },
        },
        "/interface/bridge/port": {
            "purge": {
                "id-by": "interface",
            },
        },
```

Again, the managed items under the `/interface/bridge/port` path are identified by the `interface` key and this key is
also used to select items to be purged.

For some types of items, not all subitems can be deleted. For example `/interface/bridge/vlan` will also list dynamic
VLANs which are not configured and can thus not be removed. They automatically appear/disappear with the bridge ports
using them.

In these cases, additional attributes can be specified in the `keep` option. Any item on the node that has any
attribute matching the `keep` filter will also be retained and not purged.

```
        "/interface/bridge/vlan": {
            "purge": {
                "id-by": "vlan-ids",
                "keep": {
                    "dynamic": True,
                },
            },
        },
```

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

<strong>BundleWrap will accept any attributes for these items and pass them through to the RouterOS API.</strong> All
attribute values can be passed as strings. If given as integers or booleans, BundleWrap will convert them to strings for
you. If given a set, list, or tuple of strings, BundleWrap will join those strings with commas.

Since `comment` is an internal attribute for BundleWrap, use `_comment` to apply the `comment` attribute on a RouterOS
item.

<hr>

## delete

When set to `True`, this item will be removed from the system. When using `delete`, no other attributes are allowed.
