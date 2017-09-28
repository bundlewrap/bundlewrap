# Actions

Actions will be run on every `bw apply`. They differ from regular items in that they cannot be "correct" in the first place. They can only succeed or fail.

    actions = {
        'check_if_its_still_linux': {
            'command': "uname",
            'expected_return_code': 0,
            'expected_stdout': "Linux\n",
        },
    }

<br><br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## command

The only required attribute. This is the command that will be run on the node with root privileges.

<hr>

## data_stdin

You can pipe data directly to the command running on the node. To do so, use this attribute. If it's a string or unicode object, it will always be encoded as UTF-8. Alternatively, you can use raw bytes.

<hr>

## expected_return_code

Defaults to `0`. If the return code of your command is anything else, the action is considered failed. You can also set this to `None` and any return code will be accepted.

<hr>

## expected_stdout

If this is given, the stdout output of the command must match the given string or the action is considered failed.

<hr>

## expected_stderr

Same as `expected_stdout`, but with stderr.

<hr>

## interactive

If set to `True`, this action will be skipped in non-interactive mode. If set to `False`, this action will always be executed without asking (even in interactive mode). Defaults to `None`.

<div class="alert alert-warning">Think hard before setting this to <code>False</code>. People might assume that interactive mode won't do anything without their consent.</div>
