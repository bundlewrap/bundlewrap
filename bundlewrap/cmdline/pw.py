from os.path import join
from sys import exit

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

    if op == 'bytes':
        io.stdout(repo.vault.random_bytes_as_base64_for(
            args['string'],
            key=args['key'] or 'generate',
            length=args['length'],
        ).value)

    elif op == 'decrypt':
        if args['file']:
            content = repo.vault.decrypt_file(
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
                key = args['key'] or 'encrypt'
            io.stdout(repo.vault.decrypt(
                cryptotext,
                key=key,
            ).value)

    elif op == 'encrypt':
        if args['file']:
            repo.vault.encrypt_file(
                args['string'],
                args['file'],
                key=args['key'] or 'encrypt',
            )
        else:
            io.stdout(repo.vault.encrypt(
                args['string'],
                key=args['key'] or 'encrypt',
            ))

    elif op == 'human':
        io.stdout(repo.vault.human_password_for(
            args['string'],
            key=args['key'] or 'generate',
        ).value)

    elif op == 'password':
        io.stdout(repo.vault.password_for(
            args['string'],
            key=args['key'] or 'generate',
            length=args['length'],
        ).value)
