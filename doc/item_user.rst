.. _item_user:

##########
User items
##########

Manages system user accounts.

.. code-block:: python

    users = {
        "jdoe": {
            "full_name": "Jane Doe",
            "gid": "jdoe",
            "home": "/home/jdoe",
            "password": "$6$abcdef$ghijklmnopqrstuvwxyz",
            "shell": "/bin/zsh",
            "uid": 4747,
        },
    }

Attribute reference
-------------------

``full_name``
+++++++++++++

Full name of the user.

``group``
+++++++++

Primary group of the user. May be either group name or ID.

``home``
++++++++

Path to home directory. Defaults to ``/home/USERNAME``.

``password``
++++++++++++

Hashed password as it would be returned by ``crypt()`` and written to ``/etc/shadow``.

``shell``
+++++++++

Path to login shell executable.

``uid``
+++++++

Numerical user ID. It's your job to make sure it's unique.
