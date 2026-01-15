from base64 import b64encode

from bcrypt import hashpw as bcrypt_hashpw

# This is the current (2026) default cost factor in the underlying Rust
# library. (The Python wrapper doesn't export this symbol, so we have to
# copy the value here.)
_DEFAULT_BCRYPT_COST = 12

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


def bcrypt(
    payload,
    encoding='UTF-8',
    cost=_DEFAULT_BCRYPT_COST,
    salt=None,
):
    """
    Returns a crypt line using the bcrypt algorithm (`2b`).

    These lines are useful for password hashes as used in UNIX or web
    servers.

    -   `encoding`: `payload` will be encoded using this encoding.
    -   `cost`: Use this cost factor instead of bcrypt's default.
    -   `salt`: Must be a valid bcrypt salt.
    """

    if salt is None:
        salt = _DEFAULT_BCRYPT_SALT

    # The bcrypt lib calls this "salt", but it's more than that, it also
    # includes the "2b" prefix and the cost factor.
    config = f'$2b${cost}${salt}'.encode('ASCII')

    return bcrypt_hashpw(payload.encode(encoding), config).decode(
        'ASCII'
    )
