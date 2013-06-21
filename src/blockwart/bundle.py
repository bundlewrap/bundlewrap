from string import digits, letters

VALID_NAME_CHARS = digits + letters + "-_.+"


class Bundle(object):
    """
    A collection of config items, bound to a node.
    """
    def __init__(self, node, name):
        self.name = name
        self.node = node
        self.repo = node.repo

    @staticmethod
    def validate_name(name):
        try:
            for char in name:
                assert char in VALID_NAME_CHARS
            assert not name.startswith(".")

        except AssertionError:
            return False
        return True
