from base64 import b64encode, urlsafe_b64decode
from configparser import ConfigParser
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


HUMAN_CHARS_START = list("bcdfghjklmnprstvwxz")
HUMAN_CHARS_VOWELS = list("aeiou") + ["ai", "ao", "au", "ea", "ee", "ei",
                                      "eu", "ia", "ie", "oo", "ou"]
HUMAN_CHARS_CONS = HUMAN_CHARS_START + ["bb", "bl", "cc", "ch", "ck", "dd", "dr",
                                        "ds", "dt", "ff", "gg", "gn", "kl", "ll",
                                        "mb", "md", "mm", "mp", "mt", "nc", "nd",
                                        "nn", "np", "nt", "pp", "rr", "rt", "sh",
                                        "ss", "st", "tl", "ts", "tt"]

FILENAME_SECRETS = ".secrets.cfg"


def choice_prng(lst, prng):
    return lst[next(prng) % (len(lst) - 1)]


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


class SecretProxy:
    @staticmethod
    def random_key():
        """
        Provided as a helper to generate new keys from `bw debug`.
        """
        return Fernet.generate_key().decode('utf-8')

    def __init__(self, repo):
        self.repo = repo
        self.keys = self._load_keys()

    def _decrypt(self, cryptotext=None, key=None):
        """
        Decrypts a given encrypted password.
        """
        if environ.get("BW_VAULT_DUMMY_MODE", "0") != "0":
            return "decrypted text"

        key, cryptotext = self._determine_key_to_use(cryptotext.encode('utf-8'), key, cryptotext)
        return Fernet(key).decrypt(cryptotext).decode('utf-8')

    def _decrypt_file(self, source_path=None, key=None):
        """
        Decrypts the file at source_path (relative to data/) and
        returns the plaintext as unicode.
        """
        if environ.get("BW_VAULT_DUMMY_MODE", "0") != "0":
            return "decrypted file"

        cryptotext = get_file_contents(join(self.repo.data_dir, source_path))
        key, cryptotext = self._determine_key_to_use(cryptotext, key, source_path)

        f = Fernet(key)
        return f.decrypt(cryptotext).decode('utf-8')

    def _decrypt_file_as_base64(self, source_path=None, key=None):
        """
        Decrypts the file at source_path (relative to data/) and
        returns the plaintext as base64.
        """
        if environ.get("BW_VAULT_DUMMY_MODE", "0") != "0":
            return b64encode("decrypted file as base64").decode('utf-8')

        cryptotext = get_file_contents(join(self.repo.data_dir, source_path))
        key, cryptotext = self._determine_key_to_use(cryptotext, key, source_path)

        f = Fernet(key)
        return b64encode(f.decrypt(cryptotext)).decode('utf-8')

    def _determine_key_to_use(self, cryptotext, key, entity_description):
        key_delim = cryptotext.find(b'$')
        if key_delim > -1:
            key_from_text = cryptotext[:key_delim].decode('utf-8')
            cryptotext = cryptotext[key_delim + 1:]
        else:
            key_from_text = None

        if key is None:
            if key_from_text is not None:
                key = key_from_text
            else:
                key = 'encrypt'

        try:
            key = self.keys[key]
        except KeyError:
            raise FaultUnavailable(_(
                "Key '{key}' not available for decryption of the following entity, "
                "check your {file}: {entity_description}"
            ).format(
                file=FILENAME_SECRETS,
                key=key,
                entity_description=entity_description,
            ))

        return key, cryptotext

    def _generate_human_password(
        self, identifier=None, digits=2, key='generate', per_word=3, words=4,
    ):
        """
        Like _generate_password(), but creates a password which can be
        typed more easily by human beings.

        A "word" consists of an upper case character (usually an actual
        consonant), followed by an alternating pattern of "vowels" and
        "consonants". Those lists of characters are defined at the top
        of this file. Note that something like "tl" is considered "a
        consonant" as well. Similarly, "au" and friends are "a vowel".

        Words are separated by dashes. By default, you also get some
        digits at the end of the password.
        """
        if environ.get("BW_VAULT_DUMMY_MODE", "0") != "0":
            return "generatedpassword"

        prng = self._get_prng(identifier, key)

        pwd = ""
        is_start = True
        word_length = 0
        words_done = 0
        while words_done < words:
            if is_start:
                add = choice_prng(HUMAN_CHARS_START, prng).upper()
                is_start = False
                is_vowel = True
            else:
                if is_vowel:
                    add = choice_prng(HUMAN_CHARS_VOWELS, prng)
                else:
                    add = choice_prng(HUMAN_CHARS_CONS, prng)
                is_vowel = not is_vowel
            pwd += add

            word_length += 1
            if word_length == per_word:
                pwd += "-"
                word_length = 0
                words_done += 1
                is_start = True

        if digits > 0:
            for i in range(digits):
                pwd += str(next(prng) % 10)
        else:
            # Strip trailing dash which is always added by the routine
            # above.
            pwd = pwd[:-1]

        return pwd

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
            return ("generatedpassword"*length)[:length]

        prng = self._get_prng(identifier, key)

        alphabet = ascii_letters + digits
        if symbols:
            alphabet += punctuation

        return "".join([choice_prng(alphabet, prng) for i in range(length)])

    def _generate_random_bytes_as_base64(self, identifier=None, key='generate', length=32):
        if environ.get("BW_VAULT_DUMMY_MODE", "0") != "0":
            return b64encode(bytearray([ord("a") for i in range(length)])).decode()

        prng = self._get_prng(identifier, key)
        return b64encode(bytearray([next(prng) for i in range(length)])).decode()

    def _get_prng(self, identifier, key):
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

        h = hmac.new(urlsafe_b64decode(key_encoded), digestmod=hashlib.sha512)
        h.update(identifier.encode('utf-8'))
        return random(h.digest())

    def _load_keys(self):
        config = ConfigParser()
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

    def decrypt(self, cryptotext, key=None):
        return Fault(
            'bw secrets decrypt',
            self._decrypt,
            cryptotext=cryptotext,
            key=key,
        )

    def decrypt_file(self, source_path, key=None):
        return Fault(
            'bw secrets decrypt_file',
            self._decrypt_file,
            source_path=source_path,
            key=key,
        )

    def decrypt_file_as_base64(self, source_path, key=None):
        return Fault(
            'bw secrets decrypt_file_as_base64',
            self._decrypt_file_as_base64,
            source_path=source_path,
            key=key,
        )

    def encrypt(self, plaintext, key='encrypt'):
        """
        Encrypts a given plaintext password and returns a string that can
        be fed into decrypt() to get the password back.
        """
        key_name = key
        try:
            key = self.keys[key]
        except KeyError:
            raise KeyError(_(
                "Key '{key}' not available for encryption, check your {file}"
            ).format(
                file=FILENAME_SECRETS,
                key=key,
            ))

        return key_name + '$' + Fernet(key).encrypt(plaintext.encode('utf-8')).decode('utf-8')

    def encrypt_file(self, source_path, target_path, key='encrypt'):
        """
        Encrypts the file at source_path and places the result at
        target_path. The source_path is relative to CWD or absolute,
        while target_path is relative to data/.
        """
        key_name = key
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
            f.write(key_name.encode('utf-8') + b'$')
            f.write(fernet.encrypt(plaintext))
        return target_file

    def human_password_for(
        self, identifier, digits=2, key='generate', per_word=3, words=4,
    ):
        return Fault(
            'bw secrets human_password_for',
            self._generate_human_password,
            identifier=identifier,
            digits=digits,
            key=key,
            per_word=per_word,
            words=words,
        )

    def password_for(self, identifier, key='generate', length=32, symbols=False):
        return Fault(
            'bw secrets password_for',
            self._generate_password,
            identifier=identifier,
            key=key,
            length=length,
            symbols=symbols,
        )

    def random_bytes_as_base64_for(self, identifier, key='generate', length=32):
        return Fault(
            'bw secrets random_bytes_as_base64',
            self._generate_random_bytes_as_base64,
            identifier=identifier,
            key=key,
            length=length,
        )
