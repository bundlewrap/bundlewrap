from string import digits, letters

VALID_NAME_CHARS = digits + letters + "-_.+"


def mark_for_translation(s):
    return s


def validate_name(name):
    """
    Checks whether the given string is a valid name for a node, group,
    or bundle.
    """
    try:
        for char in name:
            assert char in VALID_NAME_CHARS
        assert not name.startswith(".")
    except AssertionError:
        return False
    return True
