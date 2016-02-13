.. _item_postgres_db:

#######################
Postgres database items
#######################

Manages Postgres databases.

.. code-block:: python

    postgres_dbs = {
        "mydatabase": {
            "owner": "me",
        },
    }

Attribute reference
-------------------

.. seealso::

   :ref:`The list of generic builtin item attributes <builtin_item_attributes>`

Optional attributes
===================

``owner``
+++++++++

Name of the role which owns this database (defaults to ``"postgres"``).
