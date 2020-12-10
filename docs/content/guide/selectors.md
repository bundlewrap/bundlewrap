# Node selectors

These can be used on the command line to select a number of nodes.

See `bw apply --help` for a list of possible uses.

<br>

# Item selectors

Item selectors provide a way to address multiple items e.g. when specifying dependencies between them.

<table>
<tr><th>Example selector</th><th>Meaning</th></tr>
<tr><td><code>file:/etc/motd</code></td><td>a single item</td></tr>
<tr><td><code>file:</code></td><td>all items of that type</td></tr>
<tr><td><code>bundle:foo</code></td><td>all items in that bundle</td></tr>
<tr><td><code>tag:foo</code></td><td>all items with that tag</td></tr>
<tr><td><code>tag:</code></td><td>all items with any tag</td></tr>
</table>

All selectors can be prefixed with `!` to select the inverse (e.g. `!tag:` means "all items without any tag").
