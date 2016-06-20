from base64 import b64encode, urlsafe_b64decode
try:
    from configparser import SafeConfigParser
except ImportError:  # Python 2
    from ConfigParser import SafeConfigParser
import hashlib
import hmac
from os import environ
from os.path import join
from string import ascii_letters, punctuation, digits

from cryptography.fernet import Fernet

from .exceptions import FaultUnavailable
from .utils import Fault, get_file_contents
from .utils.text import mark_for_translation as _
from .utils.ui import io


FILENAME_SECRETS = ".secrets.cfg"


def generate_initial_secrets_cfg():
    return (
        "# DO NOT COMMIT THIS FILE\n"
        "# share it with your team through a secure channel\n\n"
        "[generate]\nkey = {}\n\n"
        "[encrypt]\nkey = {}\n"
    ).format(
        SecretProxy.random_key(),
        SecretProxy.random_key(),
    )


def random(seed):
    """
    Provides a way to get repeatable random numbers from the given seed.
    Unlike random.seed(), this approach provides consistent results
    across platforms.
    See also http://stackoverflow.com/a/18992474
    """
    while True:
        seed = hashlib.sha512(seed).digest()
        for character in seed:
            try:
                yield ord(character)
            except TypeError:  # Python 3
                yield character


class SecretProxy(object):
    @staticmethod
    def random_key():
        """
        Provided as a helper to generate new keys from `bw debug`.
        """
        return Fernet.generate_key().decode('utf-8')

    def __init__(self, repo):
        self.repo = repo
        self.keys = self._load_keys()

    def _decrypt(self, cryptotext=None, key='encrypt'):
        """
        Decrypts a given encrypted password.
        """
        if environ.get("BW_VAULT_DUMMY_MODE", "0") != "0":
            return "decrypted text"
        try:
            key = self.keys[key]
        except KeyError:
            raise FaultUnavailable(_(
                "Key '{key}' not available for decryption, check your {file}"
            ).format(
                file=FILENAME_SECRETS,
                key=key,
            ))

        return Fernet(key).decrypt(cryptotext.encode('utf-8')).decode('utf-8')

    def _decrypt_file(self, source_path=None, key='encrypt'):
        """
        Decrypts the file at source_path (relative to data/) and
        returns the plaintext as unicode.
        """
        if environ.get("BW_VAULT_DUMMY_MODE", "0") != "0":
            return "decrypted file"
        try:
            key = self.keys[key]
        except KeyError:
            raise FaultUnavailable(_(
                "Key '{key}' not available for file decryption, check your {file}"
            ).format(
                file=FILENAME_SECRETS,
                key=key,
            ))

        f = Fernet(key)
        return f.decrypt(get_file_contents(join(self.repo.data_dir, source_path))).decode('utf-8')

    def _decrypt_file_as_base64(self, source_path=None, key='encrypt'):
        """
        Decrypts the file at source_path (relative to data/) and
        returns the plaintext as base64.
        """
        if environ.get("BW_VAULT_DUMMY_MODE", "0") != "0":
            return b64encode("decrypted file as base64").decode('utf-8')
        try:
            key = self.keys[key]
        except KeyError:
            raise FaultUnavailable(_(
                "Key '{key}' not available for file decryption, check your {file}"
            ).format(
                file=FILENAME_SECRETS,
                key=key,
            ))

        f = Fernet(key)
        return b64encode(f.decrypt(get_file_contents(
            join(self.repo.data_dir, source_path),
        ))).decode('utf-8')

    def _generate_password(self, identifier=None, key='generate', length=32, symbols=False):
        """
        Derives a password from the given identifier and the shared key
        in the repository.

        This is done by seeding a random generator with an SHA512 HMAC built
        from the key and the given identifier.
        One could just use the HMAC digest itself as a password, but the
        PRNG allows for more control over password length and complexity.
        """
        if environ.get("BW_VAULT_DUMMY_MODE", "0") != "0":
            return "generatedpassword"
        try:
            key_encoded = self.keys[key]
        except KeyError:
            raise FaultUnavailable(_(
                "Key '{key}' not available to generate password '{password}', check your {file}"
            ).format(
                file=FILENAME_SECRETS,
                key=key,
                password=identifier,
            ))

        alphabet = ascii_letters + digits
        if symbols:
            alphabet += punctuation

        h = hmac.new(urlsafe_b64decode(key_encoded), digestmod=hashlib.sha512)
        h.update(identifier.encode('utf-8'))
        prng = random(h.digest())
        return "".join([alphabet[next(prng) % (len(alphabet) - 1)] for i in range(length)])

    def _load_keys(self):
        config = SafeConfigParser()
        secrets_file = join(self.repo.path, FILENAME_SECRETS)
        try:
            config.read(secrets_file)
        except IOError:
            io.debug(_("unable to read {}").format(secrets_file))
            return {}
        result = {}
        for section in config.sections():
            result[section] = config.get(section, 'key').encode('utf-8')
        return result

    def decrypt(self, cryptotext, key='encrypt'):
        return Fault(
            self._decrypt,
            cryptotext=cryptotext,
            key=key,
        )

    def decrypt_file(self, source_path, key='encrypt'):
        return Fault(
            self._decrypt_file,
            source_path=source_path,
            key=key,
        )

    def decrypt_file_as_base64(self, source_path, key='encrypt'):
        return Fault(
            self._decrypt_file_as_base64,
            source_path=source_path,
            key=key,
        )

    def encrypt(self, plaintext, key='encrypt'):
        """
        Encrypts a given plaintext password and returns a string that can
        be fed into decrypt() to get the password back.
        """
        try:
            key = self.keys[key]
        except KeyError:
            raise KeyError(_(
                "Key '{key}' not available for encryption, check your {file}"
            ).format(
                file=FILENAME_SECRETS,
                key=key,
            ))

        return Fernet(key).encrypt(plaintext.encode('utf-8')).decode('utf-8')

    def encrypt_file(self, source_path, target_path, key='encrypt'):
        """
        Encrypts the file at source_path and places the result at
        target_path. The source_path is relative to CWD or absolute,
        while target_path is relative to data/.
        """
        try:
            key = self.keys[key]
        except KeyError:
            raise KeyError(_(
                "Key '{key}' not available for file encryption, check your {file}"
            ).format(
                file=FILENAME_SECRETS,
                key=key,
            ))

        plaintext = get_file_contents(source_path)
        fernet = Fernet(key)
        target_file = join(self.repo.data_dir, target_path)
        with open(target_file, 'wb') as f:
            f.write(fernet.encrypt(plaintext))
        return target_file

    def _format(self, format_str=None, faults=None):
        return format_str.format(*[fault.value for fault in faults])

    def format(self, format_str, *faults):
        """
        Returns a Fault for a string formatted with the given Faults,
        e.g.:

            vault.format("password: {}", vault.password_for("something"))

        """
        return Fault(
            self._format,
            format_str=format_str,
            faults=faults,
        )

    def password_for(self, identifier, key='generate', length=32, symbols=False):
        return Fault(
            self._generate_password,
            identifier=identifier,
            key=key,
            length=length,
            symbols=symbols,
        )
