from base64 import b64encode
from hashlib import sha512

from bcrypt import hashpw as bcrypt_hashpw

# bcrypt needs special salts. 22 characters long, ending in ".", "O", "e", "u"
# see https://bitbucket.org/ecollins/passlib/issues/25
_DEFAULT_BCRYPT_SALT = "oo2ahgheen9Tei0IeJohTO"


def _base64_bcrypt(payload):
    payload_b64 = b64encode(payload).decode('ASCII')

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


def crypt_bcrypt(
    payload,
    encoding='UTF-8',
    rounds=12,
    salt=None,
    salt_from=None,
):
    """
    Returns a crypt line using the bcrypt algorithm (`2b`).

    These lines are useful for password hashes as used in UNIX or web
    servers.

    -   `encoding`: `payload` will be encoded using this encoding.
    -   `rounds`: Use this many rounds. `12` is the bcrypt default.
    -   `salt`: Must be a valid bcrypt salt.
    -   `salt_from`: If given, a valid bcrypt salt will be derived from
        this string. This can be something like a username. Use this
        when you don't have an actual salt value. (This is not
        necessarily "secure".)
    """

    if salt_from is not None and salt is None:
        # Derive raw bytes from the string that we got. SHA512 is
        # probably a good choice, as it normalizes the `salt_from`
        # string to a fixed length.
        #
        # The raw salt is 16 bytes long. After "base64" encoding, it is
        # 22 bytes long.
        salt = _base64_bcrypt(
            sha512(salt_from.encode('UTF-8')).digest()[:16]
        )
    elif salt is None:
        salt = _DEFAULT_BCRYPT_SALT

    # The bcrypt lib calls this "salt", but it's more than that, it also
    # includes the "2b" prefix and the number of rounds.
    config = f'$2b${rounds}${salt}'.encode('ASCII')

    return bcrypt_hashpw(payload.encode(encoding), config).decode(
        'ASCII'
    )
