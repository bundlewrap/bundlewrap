from base64 import b64encode

from bcrypt import hashpw as bcrypt_hashpw

# bcrypt salts are 16 random bytes encoded by `b64encode_bcrypt()`.
_DEFAULT_BCRYPT_SALT = "oo2ahgheen9Tei0IeJohTO"


def b64encode_bcrypt(payload_bytes):
    payload_b64 = b64encode(payload_bytes).decode('ASCII')

    # This is the standard base64 alphabet:
    alphabet_standard = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

    # Unfortunately, bcrypt uses a different one:
    # https://github.com/marshallpierce/rust-base64/blob/bc91a05e981345b7da3a5190cd3963eec6e98eb6/src/alphabet.rs#L187
    alphabet_bcrypt = './ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

    # We must now translate from the first alphabet to the second one.
    t = str.maketrans(alphabet_standard, alphabet_bcrypt)
    payload_64_bcrypt = payload_b64.translate(t)

    # The padding must also be stripped off.
    return payload_64_bcrypt.rstrip('=')


def crypt_bcrypt(payload, encoding='UTF-8', rounds=12, salt=None):
    """
    Returns a crypt line using the bcrypt algorithm (`2b`).

    These lines are useful for password hashes as used in UNIX or web
    servers.

    -   `encoding`: `payload` will be encoded using this encoding.
    -   `rounds`: Use this many rounds. `12` is the bcrypt default.
    -   `salt`: Must be a valid bcrypt salt.
    """

    if salt is None:
        salt = _DEFAULT_BCRYPT_SALT

    # The bcrypt lib calls this "salt", but it's more than that, it also
    # includes the "2b" prefix and the number of rounds.
    config = f'$2b${rounds}${salt}'.encode('ASCII')

    return bcrypt_hashpw(payload.encode(encoding), config).decode(
        'ASCII'
    )
