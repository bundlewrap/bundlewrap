from bcrypt import hashpw as bcrypt_hashpw

# bcrypt needs special salts. 22 characters long, ending in ".", "O", "e", "u"
# see https://bitbucket.org/ecollins/passlib/issues/25
_DEFAULT_BCRYPT_SALT = "oo2ahgheen9Tei0IeJohTO"


def bcrypt(b, encoding='UTF-8', rounds=12, salt=None):
    if salt is None:
        salt = _DEFAULT_BCRYPT_SALT

    # The bcrypt lib calls this "salt", but it's more than that, it also
    # includes the "2b" prefix and the number of rounds.
    config = f'$2b${rounds}${salt}'.encode('ASCII')

    return bcrypt_hashpw(b.encode(encoding), config).decode('ASCII')


# TODO #853 Add all the other hash algorithms that we need from passlib.
