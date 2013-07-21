from pipes import quote


def exists(node, path):
    """
    Returns True if the given path exists on the given node
    """
    result = node.run("test -e {}".format(quote(path)), may_fail=True)
    return result.return_code == 0
