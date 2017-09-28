# File items

Manage regular files.

    files = {
        "/path/to/file": {
            "mode": "0644",
            "owner": "root",
            "group": "root",
            "content_type": "mako",
            "encoding": "utf-8",
            "source": "my_template",
        },
    }

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## content

May be used instead of `source` to provide file content without a template file.

<hr>

## content_type

How the file pointed to by `source` or the string given to `content` should be interpreted.

<table>
<tr><th>Value</th><th>Effect</th></tr>
<tr><td><code>any</code></td><td>only cares about file owner, group, and mode</td></tr>
<tr><td><code>base64</code></td><td>content is decoded from base64</td></tr>
<tr><td><code>binary</code></td><td>file is uploaded verbatim, no content processing occurs</td></tr>
<tr><td><code>jinja2</code></td><td>content is interpreted by the Jinja2 template engine</td></tr>
<tr><td><code>mako</code></td><td>content is interpreted by the Mako template engine</td></tr>
<tr><td><code>text</code> (default)</td><td>like <code>binary</code>, but will be diffed in interactive mode</td></tr>
</table>

<hr>

## context

Only used with Mako and Jinja2 templates. The values of this dictionary will be available from within the template as variables named after the respective keys.

<hr>

## delete

When set to `True`, the path of this file will be removed. It doesn't matter if there is not a file but a directory or something else at this path. When using `delete`, no other attributes are allowed.

<hr>

## encoding

Encoding of the target file. Note that this applies to the remote file only, your template is still conveniently written in UTF-8 and will be converted by BundleWrap. Defaults to "utf-8". Other possible values (e.g. "latin-1") can be found [here](http://docs.python.org/2/library/codecs.html#standard-encodings).

<hr>

## group

Name of the group this file belongs to. Defaults to `'root'`. Set to `None` if you don't want BundleWrap to change whatever is set on the node.

<hr>

## mode

File mode as returned by `stat -c %a <file>`. Defaults to `644`. Set to `None` if you don't want BundleWrap to change whatever is set on the node.

<hr>

## owner

Username of the file's owner. Defaults to `'root'`. Set to `None` if you don't want BundleWrap to change whatever is set on the node.

<hr>

## source

File name of the file template. If this says `my_template`, BundleWrap will look in `data/my_bundle/files/my_template` and then `bundles/my_bundle/files/my_template`. Most of the time, you will want to put config templates into the latter directory. The `data/` subdirectory is meant for files that are very specific to your infrastructure (e.g. DNS zone files). This separation allows you to write your bundles in a generic way so that they could be open-sourced and shared with other people. Defaults to the filename of this item (e.g. `foo.conf` when this item is `/etc/foo.conf`).

See also: [Writing file templates](../guide/item_file_templates.md)

<hr>

## verify_with

This can be used to run external validation commands on a file before it is applied to a node. The file is verified locally on the machine running BundleWrap. Verification is considered successful when the exit code of the verification command is 0. Use `{}` as a placeholder for the shell-quoted path to the temporary file. Here is an example for verifying sudoers files:

<pre><code class="nohighlight">visudo -cf {}</code></pre>

Keep in mind that all team members will have to have the verification command installed on their machines.
