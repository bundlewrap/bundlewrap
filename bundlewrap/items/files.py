from atexit import register as at_exit
from base64 import b64decode
from collections import defaultdict
from contextlib import contextmanager, suppress
from datetime import datetime
try:
    from functools import cache
except ImportError:  # Python 3.8
    cache = lambda f: f
from hashlib import md5
from os import getenv, getpid, makedirs, mkdir, rmdir
from os.path import basename, dirname, exists, isfile, join, normpath
from shlex import quote
from shutil import rmtree
from subprocess import check_output, CalledProcessError, STDOUT
from sys import exc_info
from tempfile import gettempdir
from time import sleep
from traceback import format_exception

from jinja2 import Environment, FileSystemLoader
from mako.lookup import TemplateLookup
from mako.template import Template
from requests import head

from bundlewrap.exceptions import BundleError, FaultUnavailable, TemplateError
from bundlewrap.items import BUILTIN_ITEM_ATTRIBUTES, Item
from bundlewrap.items.directories import validator_mode
from bundlewrap.utils import cached_property, download, hash_local_file, sha1, tempfile
from bundlewrap.utils.remote import PathInfo
from bundlewrap.utils.text import bold, force_text, mark_for_translation as _
from bundlewrap.utils.text import is_subdirectory
from bundlewrap.utils.ui import io


DIFF_MAX_FILE_SIZE = 1024 * 1024 * 5  # bytes


@cache
def check_download(url, timeout):
    try:
        head(url, timeout=timeout).raise_for_status()
    except Exception as exc:
        return exc
    else:
        return None


def content_processor_base64(item):
    # .encode() is required for pypy3 only
    return b64decode(item._template_content.encode())


def content_processor_jinja2(item):
    loader = FileSystemLoader(searchpath=[item.item_data_dir, item.item_dir])
    env = Environment(loader=loader)

    template = env.from_string(item._template_content)

    io.debug(f"{item.node.name}:{item.bundle.name}:{item.id}: rendering with Jinja2...")
    start = datetime.now()
    try:
        content = template.render(
            item=item,
            bundle=item.bundle,
            node=item.node,
            repo=item.node.repo,
            **item.attributes['context']
        )
    except FaultUnavailable as e:
        io.debug(f"{item.node.name}:{item.bundle.name}:{item.id}: Fault Unavailable - {e}")
        raise
    except Exception as e:
        io.stderr("".join(format_exception(*exc_info())))
        raise TemplateError(_(
            "Error while rendering template for {node}:{bundle}:{item}: {error}"
        ).format(
            bundle=item.bundle.name,
            error=e,
            item=item.id,
            node=item.node.name,
        ))
    duration = datetime.now() - start
    io.debug("{node}:{bundle}:{item}: rendered in {time:.09f} s".format(
        bundle=item.bundle.name,
        item=item.id,
        node=item.node.name,
        time=duration.total_seconds(),
    ))
    return content.encode(item.attributes['encoding'])


def content_processor_mako(item):
    template = Template(
        item._template_content.encode('utf-8'),
        input_encoding='utf-8',
        lookup=TemplateLookup(directories=[item.item_data_dir, item.item_dir]),
        output_encoding=item.attributes['encoding'],
    )
    io.debug(f"{item.node.name}:{item.bundle.name}:{item.id}: rendering with Mako...")
    start = datetime.now()
    try:
        content = template.render(
            item=item,
            bundle=item.bundle,
            node=item.node,
            repo=item.node.repo,
            **item.attributes['context']
        )
    except FaultUnavailable as e:
        io.debug(f"{item.node.name}:{item.bundle.name}:{item.id}: Fault Unavailable - {e}")
        raise
    except Exception as e:
        io.stderr("".join(format_exception(*exc_info())))
        if isinstance(e, NameError) and str(e) == "Undefined":
            # Mako isn't very verbose here. Try to give a more useful
            # error message - even though we can't pinpoint the excat
            # location of the error. :/
            e = _("Undefined variable (look for '${...}')")
        elif isinstance(e, KeyError):
            e = _("KeyError: {}").format(str(e))
        raise TemplateError(_(
            "Error while rendering template for {node}:{bundle}:{item}: {error}"
        ).format(
            bundle=item.bundle.name,
            error=e,
            item=item.id,
            node=item.node.name,
        ))
    duration = datetime.now() - start
    io.debug(f"{item.node.name}:{item.bundle.name}:{item.id}: rendered in {duration.total_seconds():.09f} s")
    return content


def content_processor_text(item):
    return item._template_content.encode(item.attributes['encoding'])


CONTENT_PROCESSORS = {
    'any': lambda item: b"",
    'base64': content_processor_base64,
    'binary': None,
    'jinja2': content_processor_jinja2,
    'mako': content_processor_mako,
    'text': content_processor_text,
    'download': None,
}


def download_file(item):
    file_name_hashed = md5(item.attributes['source'].encode('UTF-8')).hexdigest()

    cache_path = getenv("BW_FILE_DOWNLOAD_CACHE")
    if cache_path:
        remove_dir = None
        file_path = join(cache_path, file_name_hashed)
        lock_dir = join(cache_path, "{}.bw_lock".format(file_name_hashed))

        makedirs(cache_path, exist_ok=True)
    else:
        remove_dir = join(gettempdir(), "bw-file-download-cache-{}".format(getpid()))
        file_path = join(remove_dir, file_name_hashed)
        lock_dir = join(remove_dir, "{}.bw_lock".format(file_name_hashed))

        makedirs(remove_dir, exist_ok=True)

    io.debug(f"{item.node.name}:{item.bundle.name}:{item.id}: download lock dir is {lock_dir}")

    # Since we only download the file once per process, there's no point
    # in displaying the node name here. The file may be used on multiple
    # nodes.
    with io.job(_("{}  {}  waiting for download").format(bold(item.node.name), bold(item.id))):
        while True:
            try:
                mkdir(lock_dir)
                io.debug(f"{item.node.name}:{item.bundle.name}:{item.id}: have download lock")
                break
            except FileExistsError:
                io.debug(f"{item.node.name}:{item.bundle.name}:{item.id}: waiting for download lock")
                sleep(1)

    try:
        if not isfile(file_path):
            io.debug(
                f"{item.node.name}:{item.bundle.name}:{item.id}: "
                f"starting download from {item.attributes['source']}"
            )
            with io.job(_("{node}  {item}  downloading from {url}").format(
                node=bold(item.node.name), 
                item=bold(item.id),
                url=item.attributes['source'],
            )):
                download(
                    item.attributes['source'],
                    file_path,
                    timeout=item.attributes['download_timeout'],
                )
            io.debug(
                f"{item.node.name}:{item.bundle.name}:{item.id}: "
                f"finished download from {item.attributes['source']}"
            )

        # Always do hash verification, if requested.
        if item.attributes['content_hash']:
            with io.job(_("{}  {}  checking file integrity".format(
                bold(item.node.name),
                bold(item.id),
            ))):
                local_hash = hash_local_file(file_path)
                io.debug(f"{item.node.name}:{item.bundle.name}:{item.id}: content hash is {local_hash}")
                if local_hash != item.attributes['content_hash']:
                    raise BundleError(_(
                        "could not download correct file from {} - sha1sum mismatch "
                        "(expected {}, got {})"
                    ).format(
                        item.attributes['source'],
                        item.attributes['content_hash'],
                        local_hash
                    ))
                io.debug(f"{item.node.name}:{item.bundle.name}:{item.id}: content hash matches")
    finally:
        rmdir(lock_dir)
        io.debug(f"{item.node.name}:{item.bundle.name}:{item.id}: released download lock")

    return file_path, remove_dir


def get_remote_file_contents(node, path):
    """
    Returns the contents of the given path as a string.
    """
    with tempfile() as tmp_file:
        node.download(path, tmp_file)
        with open(tmp_file, 'rb') as f:
            content = f.read()
        return content


def validator_content_type(item_id, value):
    if value not in CONTENT_PROCESSORS:
        raise BundleError(_(
            "invalid content_type for {item}: '{value}'"
        ).format(item=item_id, value=value))


ATTRIBUTE_VALIDATORS = defaultdict(lambda: lambda id, value: None)
ATTRIBUTE_VALIDATORS.update({
    'content_type': validator_content_type,
    'mode': validator_mode,
})


class File(Item):
    """
    A file.
    """
    BUNDLE_ATTRIBUTE_NAME = "files"
    ITEM_ATTRIBUTES = {
        'content': None,
        'content_type': 'text',
        'content_hash': None,
        'context': None,
        'delete': False,
        'download_timeout': 60.0,
        'encoding': "utf-8",
        'group': "root",
        'mode': "0644",
        'owner': "root",
        'source': None,
        'verify_with': None,
        'test_with': None,
    }
    ITEM_TYPE_NAME = "file"

    def __repr__(self):
        return "<File path:{} content_type:{} owner:{} group:{} mode:{} delete:{}>".format(
            quote(self.name),
            self.attributes['content_type'],
            self.attributes['owner'],
            self.attributes['group'],
            self.attributes['mode'],
            self.attributes['delete'],
        )

    @property
    def _template_content(self):
        if self.attributes['source'] is not None:
            filename = join(self.item_data_dir, self.attributes['source'])
            if not exists(filename):
                filename = join(self.item_dir, self.attributes['source'])
            with open(filename, 'rb') as f:
                return force_text(f.read())
        else:
            return force_text(self.attributes['content'])

    @cached_property
    def content(self):
        return CONTENT_PROCESSORS[self.attributes['content_type']](self)

    @cached_property
    def content_hash(self):
        if self.attributes['content_type'] in ('binary', 'download'):
            return hash_local_file(self.template)
        else:
            return sha1(self.content)

    @cached_property
    def template(self):
        if self.attributes['content_type'] == 'download':
            file_path, remove_dir = download_file(self)
            if remove_dir:
                io.debug(_("registering {} for deletion on exit").format(remove_dir))
                at_exit(rmtree, remove_dir, ignore_errors=True)
            return file_path
        data_template = join(self.item_data_dir, self.attributes['source'])
        if exists(data_template):
            return data_template
        return join(self.item_dir, self.attributes['source'])

    def cdict(self):
        if self.attributes['delete']:
            return None
        cdict = {'type': 'file'}
        if self.attributes['content_type'] != 'any':
            if self.attributes['content_type'] == 'download' and self.attributes['content_hash']:
                cdict['content_hash'] = self.attributes['content_hash']
            else:
                cdict['content_hash'] = self.content_hash
        for optional_attr in ('group', 'mode', 'owner'):
            if self.attributes[optional_attr] is not None:
                cdict[optional_attr] = self.attributes[optional_attr]
        return cdict

    def fix(self, status):
        if status.must_be_created or status.must_be_deleted or 'type' in status.keys_to_fix:
            self._fix_type(status)
        else:
            for fix_type in ('content_hash', 'mode', 'owner', 'group'):
                if fix_type in status.keys_to_fix:
                    if fix_type == 'group' and \
                            'owner' in status.keys_to_fix:
                        # owner and group are fixed with a single chown
                        continue
                    if fix_type in ('mode', 'owner', 'group') and \
                            'content' in status.keys_to_fix:
                        # fixing content implies settings mode and owner/group
                        continue
                    getattr(self, "_fix_" + fix_type)(status)

    def _fix_content_hash(self, status):
        with self._write_local_file() as local_path:
            with io.job(_("{}  {}  uploading to node").format(
                bold(self.node.name),
                bold(self.id),
            )):
                self.node.upload(
                    local_path,
                    self.name,
                    mode=self.attributes['mode'],
                    owner=self.attributes['owner'] or "",
                    group=self.attributes['group'] or "",
                    may_fail=True,
                )

    def _fix_mode(self, status):
        if self.node.os in self.node.OS_FAMILY_BSD:
            command = "chmod {} {}"
            mode = self.attributes['mode']
        else:
            command = "chmod {} -- {}"
            # GNU chmod refuses to set some modes (e.g., "chmod 0755 dir"
            # when "dir" is a directory which currently has mode "2755")
            # unless there's an additional leading zero.
            mode = '0' + self.attributes['mode'].zfill(4)
        self.run(command.format(mode, quote(self.name)))

    def _fix_owner(self, status):
        group = self.attributes['group'] or ""
        if group:
            group = ":" + quote(group)
        if self.node.os in self.node.OS_FAMILY_BSD:
            command = "chown {}{} {}"
        else:
            command = "chown {}{} -- {}"
        self.run(command.format(
            quote(self.attributes['owner'] or ""),
            group,
            quote(self.name),
        ))
    _fix_group = _fix_owner

    def _fix_type(self, status):
        if status.sdict:
            self.run("rm -rf -- {}".format(quote(self.name)))
        if not status.must_be_deleted:
            self.run("mkdir -p -- {}".format(quote(dirname(self.name))))
            self._fix_content_hash(status)

    def get_auto_deps(self, items):
        deps = []
        for item in items:
            if item.ITEM_TYPE_NAME == 'file' and is_subdirectory(item.name, self.name):
                raise BundleError(_(
                    "{item1} (from bundle '{bundle1}') blocking path to "
                    "{item2} (from bundle '{bundle2}')"
                ).format(
                    item1=item.id,
                    bundle1=item.bundle.name,
                    item2=self.id,
                    bundle2=self.bundle.name,
                ))
            elif item.ITEM_TYPE_NAME == 'user' and item.name == self.attributes['owner']:
                if item.attributes['delete']:
                    raise BundleError(_(
                        "{item1} (from bundle '{bundle1}') depends on item "
                        "{item2} (from bundle '{bundle2}') which is set to be deleted"
                    ).format(
                        item1=self.id,
                        bundle1=self.bundle.name,
                        item2=item.id,
                        bundle2=item.bundle.name,
                    ))
                else:
                    deps.append(item.id)
            elif item.ITEM_TYPE_NAME == 'group' and item.name == self.attributes['group']:
                if item.attributes['delete']:
                    raise BundleError(_(
                        "{item1} (from bundle '{bundle1}') depends on item "
                        "{item2} (from bundle '{bundle2}') which is set to be deleted"
                    ).format(
                        item1=self.id,
                        bundle1=self.bundle.name,
                        item2=item.id,
                        bundle2=item.bundle.name,
                    ))
                else:
                    deps.append(item.id)
            elif item.ITEM_TYPE_NAME in ('directory', 'symlink'):
                if is_subdirectory(item.name, self.name):
                    deps.append(item.id)
        return deps

    def sdict(self):
        path_info = PathInfo(self.node, self.name)
        if not path_info.exists:
            return None
        else:
            return {
                'type': 'file' if path_info.is_file else path_info.stat['type'],
                'content_hash': path_info.sha1 if path_info.is_file else None,
                'mode': path_info.mode,
                'owner': path_info.owner,
                'group': path_info.group,
                'size': path_info.size,
            }

    def display_on_create(self, cdict):
        if (
            self.attributes['content_type'] not in ('any', 'base64', 'binary', 'download') and
            len(self.content) < DIFF_MAX_FILE_SIZE
        ):
            del cdict['content_hash']
            cdict['content'] = force_text(self.content)
        if self.attributes['content_type'] == 'download':
            cdict['source'] = self.attributes['source']
        del cdict['type']
        return cdict

    def display_dicts(self, cdict, sdict, keys):
        if (
            'content_hash' in keys and
            self.attributes['content_type'] not in ('base64', 'binary', 'download') and
            sdict['size'] < DIFF_MAX_FILE_SIZE and
            len(self.content) < DIFF_MAX_FILE_SIZE and
            PathInfo(self.node, self.name).is_text_file
        ):
            keys.remove('content_hash')
            keys.append('content')
            del cdict['content_hash']
            del sdict['content_hash']
            cdict['content'] = self.content.decode(self.attributes['encoding'])
            sdict['content'] = get_remote_file_contents(
                self.node,
                self.name,
            ).decode('utf-8', 'backslashreplace')
        if 'type' in keys:
            with suppress(ValueError):
                keys.remove('content_hash')
        if self.attributes['content_type'] == 'download':
            cdict['source'] = self.attributes['source']
            sdict['source'] = ''
        if sdict:
            del sdict['size']
            if self.attributes['content_type'] == 'any':
                with suppress(KeyError):
                    del sdict['content_hash']
        return (cdict, sdict, keys)

    def display_on_delete(self, sdict):
        del sdict['content_hash']
        path_info = PathInfo(self.node, self.name)
        if (
            sdict['size'] < DIFF_MAX_FILE_SIZE and
            path_info.is_text_file
        ):
            sdict['content'] = get_remote_file_contents(self.node, self.name)
        if path_info.is_file:
            sdict['size'] = f"{sdict['size']} bytes"
        return sdict

    def patch_attributes(self, attributes):
        if (
            'content' not in attributes and
            'source' not in attributes and
            attributes.get('content_type', 'text') != 'any' and
            attributes.get('delete', False) is False
        ):
            attributes['source'] = basename(self.name)
        if 'context' not in attributes:
            attributes['context'] = {}
        if 'mode' in attributes and attributes['mode'] is not None:
            attributes['mode'] = str(attributes['mode']).zfill(4)
        if 'group' not in attributes and self.node.os in self.node.OS_FAMILY_BSD:
            # BSD doesn't have a root group, so we have to use a
            # different default value here
            attributes['group'] = 'wheel'
        return attributes

    def preview(self):
        if (
            self.attributes['content_type'] in ('any', 'base64', 'binary') or
            self.attributes['delete'] is True
        ):
            raise ValueError
        return self.content.decode(self.attributes['encoding'])

    def test(self):
        if (
            self.attributes['source']
            and self.attributes['content_type'] != 'download'
            and not exists(self.template)
        ):
            raise BundleError(_(
                "{item} from bundle '{bundle}' refers to missing "
                "file '{path}' in its 'source' attribute"
            ).format(
                bundle=self.bundle.name,
                item=self.id,
                path=self.template,
            ))

        if (
            self.attributes['delete']
            or self.attributes['content_type'] == 'any'
        ):
            pass
        elif (
            self.attributes['content_type'] == 'download'
            and not self.attributes['content_hash']
        ):
            download_exc = check_download(
                self.attributes['source'],
                self.attributes['download_timeout'],
            )
            if download_exc is not None:
                raise download_exc
        else:
            with self._write_local_file() as local_path:
                if self.attributes['test_with']:
                    cmd = self.attributes['test_with'].format(quote(local_path))
                    exitcode, stdout = self._run_validator(cmd)
                    if exitcode == 0:
                        io.debug(f"{self.id} passed local validation")
                    elif exitcode in (126, 127, 255):
                        io.debug(f"{self.id} failed local validation with code {exitcode}, ignoring")
                    else:
                        raise BundleError(_(
                            "{i} failed local validation using: {c}\n\n{out}"
                        ).format(
                            c=cmd,
                            i=self.id,
                            out=stdout,
                        ))

    def _run_validator(self, cmd):
        io.debug(f"calling local validator for {self.node.name}:{self.id}: {cmd}")
        try:
            p = check_output(cmd, shell=True, stderr=STDOUT)
        except CalledProcessError as e:
            return e.returncode, e.output.decode()
        else:
            return 0, p.decode()

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if attributes.get('delete', False):
            for attr in attributes.keys():
                if attr not in ['delete'] + list(BUILTIN_ITEM_ATTRIBUTES.keys()):
                    raise BundleError(_(
                        "{item} from bundle '{bundle}' cannot have other "
                        "attributes besides 'delete'"
                    ).format(item=item_id, bundle=bundle.name))

        if 'content' in attributes and 'source' in attributes:
            raise BundleError(_(
                "{item} from bundle '{bundle}' cannot have both 'content' and 'source'"
            ).format(item=item_id, bundle=bundle.name))

        if 'content' in attributes and attributes.get('content_type') == 'binary':
            raise BundleError(_(
                "{item} from bundle '{bundle}' cannot have binary inline content "
                "(use content_type 'base64' instead)"
            ).format(item=item_id, bundle=bundle.name))

        if 'content_hash' in attributes and attributes.get('content_type') != 'download':
            raise BundleError(_(
                "{item} from bundle '{bundle}' specified 'content_hash', but is "
                "not of type 'download'"
            ).format(item=item_id, bundle=bundle.name))

        if 'download_timeout' in attributes and attributes.get('content_type') != 'download':
            raise BundleError(_(
                "{item} from bundle '{bundle}' specified 'download_timeout', but is "
                "not of type 'download'"
            ).format(item=item_id, bundle=bundle.name))

        if 'download_timeout' in attributes:
            if (
                not isinstance(attributes['download_timeout'], float)
                or attributes['download_timeout'] <= 0.0
            ):
                raise BundleError(_(
                    "download_timeout for {item} from bundle '{bundle}' must be a float > 0.0"
                ).format(item=item_id, bundle=bundle.name))

        if attributes.get('content_type') == 'download':
            if 'source' not in attributes:
                raise BundleError(_(
                    "{item} from bundle '{bundle}' is of type 'download', but missing "
                    "required attribute 'source'"
                ).format(item=item_id, bundle=bundle.name))
            elif '://' not in attributes['source']:
                raise BundleError(_(
                    "{item} from bundle '{bundle}' is of type 'download', but {source} "
                    "does not look like a URL"
                ).format(item=item_id, bundle=bundle.name, source=attributes['source']))

        if 'encoding' in attributes and attributes.get('content_type') in (
            'any',
            'base64',
            'binary',
            'download',
        ):
            raise BundleError(_(
                "content_type of {item} from bundle '{bundle}' cannot provide different encoding "
                "(remove the 'encoding' attribute)"
            ).format(item=item_id, bundle=bundle.name))

        if (
            attributes.get('content_type', None) == "any" and (
                'content' in attributes or
                'encoding' in attributes or
                'source' in attributes
            )
        ):
            raise BundleError(_(
                "{item} from bundle '{bundle}' with content_type 'any' "
                "must not define 'content', 'encoding' and/or 'source'"
            ).format(item=item_id, bundle=bundle.name))

        for key, value in attributes.items():
            ATTRIBUTE_VALIDATORS[key](item_id, value)

    @classmethod
    def validate_name(cls, bundle, name):
        if normpath(name) == "/":
            raise BundleError(_("'/' cannot be a file"))
        if normpath(name) != name:
            raise BundleError(_(
                "'{path}' is an invalid file path, should be '{normpath}' (bundle '{bundle}')"
            ).format(
                bundle=bundle.name,
                normpath=normpath(name),
                path=name,
            ))

    @contextmanager
    def _write_local_file(self):
        """
        Makes the file contents available at the returned temporary path
        and performs local verification if necessary or requested.

        The calling method is responsible for cleaning up the file at
        the returned path (only if not a binary).
        """
        with tempfile() as tmp_file:
            if self.attributes['content_type'] in ('binary', 'download'):
                local_path = self.template
            else:
                local_path = tmp_file
                with open(local_path, 'wb') as f:
                    f.write(self.content)

            if self.attributes['verify_with']:
                cmd = self.attributes['verify_with'].format(quote(local_path))
                exitcode, stdout = self._run_validator(cmd)
                if exitcode == 0:
                    io.debug(f"{self.id} passed local validation")
                else:
                    raise BundleError(_(
                        "{i} failed local validation using: {c}\n\n{out}"
                    ).format(
                        c=cmd,
                        i=self.id,
                        out=stdout,
                    ))

            yield local_path
