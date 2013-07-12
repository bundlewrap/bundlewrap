from collections import defaultdict

from blockwart.exceptions import BundleError
from blockwart.items import Item, ItemStatus
from blockwart.utils import mark_for_translation as _


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

ATTRIBUTE_VALIDATORS = defaultdict(lambda: lambda value: None)
ATTRIBUTE_VALIDATORS.update({
    'mode': validator_mode,
})


class File(Item):
    """
    A file.
    """
    BUNDLE_ATTRIBUTE_NAME = "files"
    DEPENDS_STATIC = []
    ITEM_ATTRIBUTES = {
        'group': "root",
        'mode': "0664",
        'owner': "root",
    }
    ITEM_TYPE_NAME = "file"

    def ask(self):
        return ""

    def fix(self):
        raise NotImplementedError

    def get_status(self):
        return ItemStatus(
            correct=True,
            description="No description available.",
            status_info={},
        )

    def validate_attributes(self, attributes):
        for key, value in attributes.items():
            ATTRIBUTE_VALIDATORS[key](self.id, value)
