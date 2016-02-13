.. _item_postgres_role:

###################
Postgres role items
###################

Manages Postgres roles.

.. code-block:: python

    postgres_roles = {
        "me": {
            "superuser": True,
            "password": "itsamemario",
        },
    }

Attribute reference
-------------------

.. seealso::

   :ref:`The list of generic builtin item attributes <builtin_item_attributes>`

Optional attributes
===================

``superuser``
+++++++++++++

``True`` if the role should be given superuser privileges (defaults to ``False``).

|

``password``
++++++++++++

Plaintext password to set for this role (will be hashed using MD5).

.. warning::
   Please do not write any passwords into your bundles. This attribute is intended to be used with an external source of passwords and filled dynamically. If you don't have or want such an elaborate setup, specify passwords using the ``password_hash`` attribute instead.

|

``password_hash``
+++++++++++++++++

As an alternative to ``password``, this allows setting the raw hash as it will be stored in Postgres' internal database. Should start with "md5".
