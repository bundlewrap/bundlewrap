from base64 import b64decode
from collections import defaultdict
from contextlib import contextmanager, suppress
from datetime import datetime
from os.path import basename, dirname, exists, join, normpath
from shlex import quote
from subprocess import call
from sys import exc_info
from traceback import format_exception

from jinja2 import Environment, FileSystemLoader
from mako.lookup import TemplateLookup
from mako.template import Template

from bundlewrap.exceptions import BundleError, FaultUnavailable, TemplateError
from bundlewrap.items import BUILTIN_ITEM_ATTRIBUTES, Item
from bundlewrap.items.directories import validator_mode
from bundlewrap.utils import cached_property, hash_local_file, sha1, tempfile
from bundlewrap.utils.remote import PathInfo
from bundlewrap.utils.text import force_text, mark_for_translation as _
from bundlewrap.utils.text import is_subdirectory
from bundlewrap.utils.ui import io


DIFF_MAX_FILE_SIZE = 1024 * 1024 * 5  # bytes


def content_processor_base64(item):
    # .encode() is required for pypy3 only
    return b64decode(item._template_content.encode())


def content_processor_jinja2(item):
    loader = FileSystemLoader(searchpath=[item.item_data_dir, item.item_dir])
    env = Environment(loader=loader)

    template = env.from_string(item._template_content)

    io.debug("{node}:{bundle}:{item}: rendering with Jinja2...".format(
        bundle=item.bundle.name,
        item=item.id,
        node=item.node.name,
    ))
    start = datetime.now()
    try:
        content = template.render(
            item=item,
            bundle=item.bundle,
            node=item.node,
            repo=item.node.repo,
            **item.attributes['context']
        )
    except FaultUnavailable:
        raise
    except Exception as e:
        io.debug("".join(format_exception(*exc_info())))
        raise TemplateError(_(
            "Error while rendering template for {node}:{bundle}:{item}: {error}"
        ).format(
            bundle=item.bundle.name,
            error=e,
            item=item.id,
            node=item.node.name,
        ))
    duration = datetime.now() - start
    io.debug("{node}:{bundle}:{item}: rendered in {time}s".format(
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
    io.debug("{node}:{bundle}:{item}: rendering with Mako...".format(
        bundle=item.bundle.name,
        item=item.id,
        node=item.node.name,
    ))
    start = datetime.now()
    try:
        content = template.render(
            item=item,
            bundle=item.bundle,
            node=item.node,
            repo=item.node.repo,
            **item.attributes['context']
        )
    except FaultUnavailable:
        raise
    except Exception as e:
        io.debug("".join(format_exception(*exc_info())))
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
    io.debug("{node}:{bundle}:{item}: rendered in {time}s".format(
        bundle=item.bundle.name,
        item=item.id,
        node=item.node.name,
        time=duration.total_seconds(),
    ))
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
}


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
        'context': None,
        'delete': False,
        'encoding': "utf-8",
        'group': "root",
        'mode': "0644",
        'owner': "root",
        'source': None,
        'verify_with': None,
    }
    ITEM_TYPE_NAME = "file"

    def __repr__(self):
        return "<File path:{}>".format(quote(self.name))

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
        if self.attributes['content_type'] == 'binary':
            return hash_local_file(self.template)
        else:
            return sha1(self.content)

    @cached_property
    def template(self):
        data_template = join(self.item_data_dir, self.attributes['source'])
        if exists(data_template):
            return data_template
        return join(self.item_dir, self.attributes['source'])

    def cdict(self):
        if self.attributes['delete']:
            return None
        cdict = {'type': 'file'}
        if self.attributes['content_type'] != 'any':
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
        else:
            command = "chmod {} -- {}"
        self.run(command.format(
            self.attributes['mode'],
            quote(self.name),
        ))

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
            if item.ITEM_TYPE_NAME == "file" and is_subdirectory(item.name, self.name):
                raise BundleError(_(
                    "{item1} (from bundle '{bundle1}') blocking path to "
                    "{item2} (from bundle '{bundle2}')"
                ).format(
                    item1=item.id,
                    bundle1=item.bundle.name,
                    item2=self.id,
                    bundle2=self.bundle.name,
                ))
            elif item.ITEM_TYPE_NAME == "user" and item.name == self.attributes['owner']:
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
            elif item.ITEM_TYPE_NAME == "group" and item.name == self.attributes['group']:
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
            elif item.ITEM_TYPE_NAME in ("directory", "symlink"):
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

    def display_dicts(self, cdict, sdict, keys):
        if (
            'content_hash' in keys and
            self.attributes['content_type'] not in ('base64', 'binary') and
            sdict['size'] < DIFF_MAX_FILE_SIZE and
            len(self.content) < DIFF_MAX_FILE_SIZE and
            PathInfo(self.node, self.name).is_text_file
        ):
            keys.remove('content_hash')
            keys.append('content')
            del cdict['content_hash']
            del sdict['content_hash']
            cdict['content'] = self.content
            sdict['content'] = get_remote_file_contents(self.node, self.name)
        if 'type' in keys:
            with suppress(ValueError):
                keys.remove('content_hash')
        return (cdict, sdict, keys)

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
        if self.attributes['source'] and not exists(self.template):
            raise BundleError(_(
                "{item} from bundle '{bundle}' refers to missing "
                "file '{path}' in its 'source' attribute"
            ).format(
                bundle=self.bundle.name,
                item=self.id,
                path=self.template,
            ))

        if not self.attributes['delete'] and not self.attributes['content_type'] == 'any':
            with self._write_local_file():
                pass

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

        if 'encoding' in attributes and attributes.get('content_type') in (
            'any',
            'base64',
            'binary',
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
            if self.attributes['content_type'] == 'binary':
                local_path = self.template
            else:
                local_path = tmp_file
                with open(local_path, 'wb') as f:
                    f.write(self.content)

            if self.attributes['verify_with']:
                cmd = self.attributes['verify_with'].format(quote(local_path))
                io.debug("calling local verify command for {i}: {c}".format(c=cmd, i=self.id))
                if call(cmd, shell=True) == 0:
                    io.debug("{i} passed local validation".format(i=self.id))
                else:
                    raise BundleError(_(
                        "{i} failed local validation using: {c}"
                    ).format(c=cmd, i=self.id))

            yield local_path
