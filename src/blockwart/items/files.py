from collections import defaultdict
from os.path import join

from blockwart.exceptions import BundleError
from blockwart.items import Item, ItemStatus
from blockwart.utils import cached_property, sha1
from blockwart.utils.remote import PathInfo
from blockwart.utils.text import mark_for_translation as _

CONTENT_PROCESSORS = {
    'binary': None,
}


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
        return ""

    def fix(self, status):
        CONTENT_PROCESSORS[self.attributes['content_type']](self.attributes)

    def get_status(self):
        correct = True
        path_info = PathInfo(self.node, self.name)
        status_info = {'needs_fixing': [], 'path_info': path_info}

        if path_info.mode != self.attributes['mode']:
            status_info['needs_fixing'].append('mode')
        if path_info.owner != self.attributes['owner'] or \
                path_info.group != self.attributes['group']:
            status_info['needs_fixing'].append('owner')
        if path_info.sha1 != self.content_hash:
            status_info['needs_fixing'].append('content')
        if not path_info.is_file:
            status_info['needs_fixing'].append('type')

        if status_info['needs_fixing']:
            correct = False
        return ItemStatus(correct=correct, info=status_info)

    def validate_attributes(self, attributes):
        for key, value in attributes.items():
            ATTRIBUTE_VALIDATORS[key](self.id, value)
