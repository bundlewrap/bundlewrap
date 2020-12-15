<h1>bundle.py</h1>

Within each bundle, there may be a file called `bundle.py`. It can be used to add dependencies and such to all items with a given tag (see [items.py](items.py.md) for a general introduction to these concepts).

Here's an example:

    tags = {
        'foo': {
            'needs': {
                'svc_systemd:bar',
            },
            'triggers': {
                'action:baz',
            },
        },
    }

With this, whenever you add the `foo` tag to an item in `items.py`, that item will also depend on `svc_systemd:bar` and trigger `action:baz`.

Supported item attributes are:
* `needs`
* `needed_by`
* `precedes`
* `preceded_by`
* `triggers`
* `triggered_by`

See [Selectors](../guide/selectors.md) for a complete overview of the ways to specify items here.
