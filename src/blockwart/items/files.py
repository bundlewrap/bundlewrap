from collections import defaultdict
from difflib import unified_diff
from os import remove
from os.path import join
from pipes import quote
from tempfile import mkstemp

from blockwart.exceptions import BundleError
from blockwart.items import Item, ItemStatus
from blockwart.utils import cached_property, LOG, sha1
from blockwart.utils.remote import PathInfo
from blockwart.utils.text import mark_for_translation as _


def content_processor_mako(item):
    from mako.lookup import TemplateLookup
    lookup = TemplateLookup(
        directories=[item.item_dir],
        input_encoding='utf-8',
    )
    template = lookup.get_template(item.attributes['source'])
    return template.render(item=item, bundle=item.bundle, node=item.node,
                           repo=item.node.repo)

CONTENT_PROCESSORS = {
    'binary': None,
    'mako': content_processor_mako,
}


def diff(content_old, content_new, filename):
    output = ""
    for line in unified_diff(
        content_old.split("\n"),
        content_new.split("\n"),
        fromfile=filename,
        tofile=_("<blockwart content>"),
    ):
        output += line + "\n"
    return output


def get_remote_file_contents(node, path):
    """
    Returns the contents of the given path as a string.
    """
    handle, tmp_file = mkstemp()
    node.download(path, tmp_file)
    with open(tmp_file) as f:
        content = f.read()
    remove(tmp_file)
    return content


def hash_local_file(path):
    """
    Retuns the sha1 hash of a file on the local machine.
    """
    with open(path, 'rb') as f:
        sha1_hash = sha1(f.read())
    return sha1_hash


def validator_content_type(item_id, value):
    if value not in CONTENT_PROCESSORS:
        raise BundleError(
            _("invalid content_type for {}: '{}'").format(item_id, value)
        )


def validator_mode(item_id, value):
    if not value.isdigit():
        raise BundleError(
            _("mode for {} should be written as digits, got: '{}'"
              "").format(item_id, value)
        )
    for digit in value:
        if int(digit) > 7 or int(digit) < 0:
            raise BundleError(
                _("invalid mode for {}: '{}'").format(item_id, value),
            )
    if not len(value) == 3 and not len(value) == 4:
        raise BundleError(
            _("mode for {} should be three or four digits long, was: '{}'"
              "").format(item_id, value)
        )

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
    DEPENDS_STATIC = []
    ITEM_ATTRIBUTES = {
        'content': None,
        'content_type': "binary",
        'group': "root",
        'mode': "0664",
        'owner': "root",
        'source': None,
    }
    ITEM_TYPE_NAME = "file"

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
        return join(self.item_dir, self.attributes['source'])

    def ask(self, status):
        if 'type' in status.info['needs_fixing']:
            return _(
                "Not a regular file. "
                "The `file` utility says it's a '{}'.\n"
                "Do you want it removed and replaced?"
            ).format(
                self.name,
                status.info['path_info'].desc,
            )

        question = ""

        if 'content' in status.info['needs_fixing']:
            question += _("Wrong contents.\n")
            if status.info['path_info'].is_text_file and \
                    not self.attributes['content_type'] == 'binary':
                content_is = get_remote_file_contents(self.node, self.name)
                content_should = self.content
                question += diff(content_is, content_should, self.name)
            else:
                question += _(
                    "According to the `file` utility, it contains '{}'.\n"
                ).format(status.info['path_info'].desc)

        if 'mode' in status.info['needs_fixing']:
            question += _(
                "Mode is {}, should be {}.\n"
            ).format(
                status.info['path_info'].mode,
                self.attributes['mode'],
            )

        if 'owner' in status.info['needs_fixing']:
            question += _(
                "Owner/group is '{}:{}', should be '{}:{}'.\n"
            ).format(
                status.info['path_info'].owner,
                status.info['path_info'].group,
                self.attributes['owner'],
                self.attributes['group'],
            )

        return question + _("Fix file '{}'?").format(self.name)

    def fix(self, status):
        for fix_type in ('type', 'content', 'mode', 'owner'):
            if fix_type in status.info['needs_fixing']:
                LOG.debug(_("fixing {} of {} on {}").format(
                    fix_type,
                    self.name,
                    self.node.name,
                ))
                getattr(self, "_fix_" + fix_type)(status)

    def _fix_content(self, status):
        if self.attributes['content_type'] == 'binary':
            local_path = self.template
        else:
            handle, local_path = mkstemp()
            with open(local_path, 'w') as f:
                f.write(self.content)
        try:
            self.node.upload(local_path, self.name)
        finally:
            if self.attributes['content_type'] != 'binary':
                remove(local_path)

    def _fix_mode(self, status):
        self.node.run("chmod {} {}".format(
            self.attributes['mode'],
            quote(self.name),
        ))

    def _fix_owner(self, status):
        self.node.run("chown {}:{} {}".format(
            quote(self.attributes['owner']),
            quote(self.attributes['group']),
            quote(self.name),
        ))

    def _fix_type(self, status):
        self.node.run("rm -rf {}".format(quote(self.name)))

    def get_status(self):
        correct = True
        path_info = PathInfo(self.node, self.name)
        status_info = {'needs_fixing': [], 'path_info': path_info}

        if not path_info.is_file:
            status_info['needs_fixing'] += ['type', 'content', 'mode', 'owner']
        else:
            if path_info.mode != self.attributes['mode']:
                status_info['needs_fixing'].append('mode')
            if path_info.owner != self.attributes['owner'] or \
                    path_info.group != self.attributes['group']:
                status_info['needs_fixing'].append('owner')
            if path_info.sha1 != self.content_hash:
                status_info['needs_fixing'] += ['content', 'mode', 'owner']

        if status_info['needs_fixing']:
            correct = False
        return ItemStatus(correct=correct, info=status_info)

    def validate_attributes(self, attributes):
        for key, value in attributes.items():
            ATTRIBUTE_VALIDATORS[key](self.id, value)
