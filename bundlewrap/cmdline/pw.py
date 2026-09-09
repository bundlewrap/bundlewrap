from os.path import join
from sys import exit

from ..utils.cmdline import get_node
from ..utils.text import mark_for_translation as _, red
from ..utils.ui import io


OPERATIONS = (
    'bytes',
    'decrypt',
    'encrypt',
    'human',
    'password',
)


def get_operation(args):
    opcount = 0
    selected_op = None
    for op in OPERATIONS:
        if args[op]:
            selected_op = op
            opcount += 1
    if opcount > 1:
        io.stdout(_("{x} More than one operation selected").format(x=red("!!!")))
        exit(1)
    elif opcount == 0:
        return 'password'
    return selected_op


def bw_pw(repo, args):
    if args['length'] < 1:
        io.stdout(_("{x} length must be > 1").format(x=red("!!!")))
        exit(1)

    op = get_operation(args)

    if args['node'] is None:
        vault = repo.vault
        generate_key = args['key'] or 'generate'
        encrypt_key = args['key'] or 'encrypt'
    else:
        # node.vault fills in the node's keys for key=None
        vault = get_node(repo, args['node']).vault
        generate_key = args['key']
        encrypt_key = args['key']

    if op == 'bytes':
        io.stdout(vault.random_bytes_as_base64_for(
            args['string'],
            key=generate_key,
            length=args['length'],
        ).value)

    elif op == 'decrypt':
        if args['file']:
            content = vault.decrypt_file(
                args['string'],
                key=args['key'],
                binary=True,
            ).value
            with open(join(repo.data_dir, args['file']), 'wb') as f:
                f.write(content)
        else:
            try:
                key, cryptotext = args['string'].split("$", 1)
            except ValueError:
                cryptotext = args['string']
                key = encrypt_key
            io.stdout(vault.decrypt(
                cryptotext,
                key=key,
            ).value)

    elif op == 'encrypt':
        if args['file']:
            vault.encrypt_file(
                args['string'],
                args['file'],
                key=encrypt_key,
            )
        else:
            io.stdout(vault.encrypt(
                args['string'],
                key=encrypt_key,
            ))

    elif op == 'human':
        io.stdout(vault.human_password_for(
            args['string'],
            key=generate_key,
        ).value)

    elif op == 'password':
        io.stdout(vault.password_for(
            args['string'],
            key=generate_key,
            length=args['length'],
        ).value)
