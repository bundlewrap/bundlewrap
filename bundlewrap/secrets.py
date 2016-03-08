try:
    from configparser import SafeConfigParser
except ImportError:  # Python 2
    from ConfigParser import SafeConfigParser
import hashlib
import hmac
from os.path import join
from string import ascii_letters, punctuation, digits

from cryptography.fernet import Fernet

from .exceptions import FaultUnavailable
from .utils.text import mark_for_translation as _
from .utils.ui import io


FILENAME_SECRETS = ".secrets.cfg"


class Fault(object):
    """
    A proxy object for lazy access to things that may not really be
    available at the time of use.

    This let's us gracefully skip items that require information that's
    currently not available.
    """
    def __init__(self, callback, **kwargs):
        self._available = None
        self._exc = None
        self._value = None
        self.callback = callback
        self.kwargs = kwargs

    def _resolve(self):
        if self._available is None:
            try:
                self._value = self.callback(**self.kwargs)
                self._available = True
            except FaultUnavailable as exc:
                self._available = False
                self._exc = exc

    def __str__(self):
        return str(self.resolved)

    @property
    def is_available(self):
        self._resolve()
        return self._available

    @property
    def value(self):
        self._resolve()
        if not self._available:
            raise self._exc
        return self._value


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

    def _generate_password(self, identifier=None, key='generate', length=32, symbols=False):
        """
        Derives a password from the given identifier and the shared key
        in the repository.

        This is done by seeding a random generator with an SHA512 HMAC built
        from the key and the given identifier.
        One could just use the HMAC digest itself as a password, but the
        PRNG allows for more control over password length and complexity.
        """
        try:
            key = self.keys[key]
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

        h = hmac.new(key, digestmod=hashlib.sha512)
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

    def password_for(self, identifier, key='generate', length=32, symbols=False):
        return Fault(
            self._generate_password,
            identifier=identifier,
            key=key,
            length=length,
            symbols=symbols,
        )
