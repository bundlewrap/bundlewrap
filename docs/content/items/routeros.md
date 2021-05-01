# RouterOS items

Manages RouterOS configuration through the API (port 8728). You can address every configuration exposed by the API by constructing the item name and attributes accordingly. If you haven't already, familiarize yourself with the CLI over SSH first. Use it as a reference when composing items in your bundles. <strong>Don't forget to set the <code>os</code> attribute of your node to <code>routeros</code> and also set the <code>username</code> and <code>password</code> attributes.</strong>

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
        "/interface/bridge?name=bridge": {},
        "/interface/bridge/port?interface=ether8": {
            "bridge": "bridge",
            "needs": {
                "routeros:/interface/bridge?name=bridge",
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
    }

Note that when you're dealing with a list of things, item names have two parts, separated by a `?` character. The first part determines which kind of item is addressed, the second part is a simple `key=value` query that MUST return exactly one entry.

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

<strong>BundleWrap will accept any attributes for these items and pass them through to the RouterOS API.</strong> All attribute values can be passed as strings. If given as integers or booleans, BundleWrap will convert them to strings for you. If given a set, list, or tuple of strings, BundleWrap will join those strings with commas.

<hr>

## delete

When set to `True`, this item will be removed from the system. When using `delete`, no other attributes are allowed.
