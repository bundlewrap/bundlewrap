from blockwart.items import Item, ItemStatus


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
        pass
