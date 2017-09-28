# User items

Manages system user accounts.

    users = {
        "jdoe": {
            "full_name": "Jane Doe",
            "gid": 2342,
            "groups": ["admins", "users", "wheel"],
            "home": "/home/jdoe",
            "password_hash": "$6$abcdef$ghijklmnopqrstuvwxyz",
            "shell": "/bin/zsh",
            "uid": 4747,
        },
    }

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

All attributes are optional.

<hr>

## delete

When set to `True`, this user will be removed from the system. Note that because of how `userdel` works, the primary group of the user will be removed if it contains no other users. When using `delete`, no other attributes are allowed.

<hr>

## full_name

Full name of the user.

<hr>

## gid

Primary group of the user as numerical ID or group name.

<div class="alert alert-info">Due to how <code>useradd</code> works, this attribute is required whenever you <strong>don't</strong> want the default behavior of <code>useradd</code> (usually that means automatically creating a group with the same name as the user). If you want to use an unmanaged group already on the node, you need this attribute. If you want to use a group managed by BundleWrap, you need this attribute. This is true even if the groups mentioned are in fact named like the user.</div>

<hr>

## groups

List of groups (names, not GIDs) the user should belong to. Must NOT include the group referenced by `gid`.

<hr>

## hash_method

One of:

* `md5`
* `sha256`
* `sha512`

Defaults to `sha512`.

<hr>

## home

Path to home directory. Defaults to `/home/USERNAME`.

<hr>

## password

The user's password in plaintext.

<div class="alert alert-danger">Please do not write any passwords into your bundles. This attribute is intended to be used with an external source of passwords and filled dynamically. If you don't have or want such an elaborate setup, specify passwords using the <code>password_hash</code> attribute instead.</div>

<div class="alert alert-info">If you don't specify a <code>salt</code> along with the password, BundleWrap will use a static salt. Be aware that this is basically the same as using no salt at all.</div>

<hr>

## password_hash

Hashed password as it would be returned by `crypt()` and written to `/etc/shadow`.

<hr>

## salt

Recommended for use with the `password` attribute. BundleWrap will use 5000 rounds of SHA-512 on this salt and the provided password.

<hr>

## shell

Path to login shell executable.

<hr>

## uid

Numerical user ID. It's your job to make sure it's unique.
