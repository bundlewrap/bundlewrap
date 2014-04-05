.. _item_user:

##########
User items
##########

Manages system user accounts.

.. code-block:: python

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


Attribute reference
-------------------

.. seealso::

   :ref:`The list of generic builtin item attributes <builtin_item_attributes>`

All attributes are optional.

|

``delete``
++++++++++

When set to ``True``, this user will be removed from the system. Note that because of how :command:`userdel` works, the primary group of the user will be removed if it contains no other users. When using ``delete``, no other attributes are allowed.

|

``full_name``
+++++++++++++

Full name of the user.

|

``gid``
+++++++

Primary group of the user as numerical ID or group name.

|

``groups``
++++++++++

List of groups (names, not GIDs) the user should belong to. MUST include the group referenced by ``gid``.

|

``hash_method``
+++++++++++++++

One of:

* ``md5``
* ``sha256``
* ``sha512``

Defaults to ``sha512``.

|

``home``
++++++++

Path to home directory. Defaults to ``/home/USERNAME``.

|

``password``
++++++++++++

The user's password in plaintext.

.. warning::
   Please do not write any passwords into your bundles. This attribute is intended to be used with an external source of passwords and filled dynamically. If you don't have or want such an elaborate setup, specify passwords using the ``password_hash`` attribute instead.

.. note::
   If you don't specify a ``salt`` along with the password, Blockwart will use a static salt. Be aware that this is basically the same as using no salt at all.

|

``password_hash``
+++++++++++++++++

Hashed password as it would be returned by ``crypt()`` and written to :file:`/etc/shadow`.

|

``salt``
++++++++

Recommended for use with the ``password`` attribute. Blockwart will use 5000 rounds of SHA-512 on this salt and the provided password.

|

``shell``
+++++++++

Path to login shell executable.

|

``uid``
+++++++

Numerical user ID. It's your job to make sure it's unique.

|
