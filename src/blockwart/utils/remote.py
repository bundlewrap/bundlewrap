from pipes import quote


def _parse_file_output(file_output):
    if file_output.startswith("cannot open `"):
        return ('nonexistent', "")
    elif file_output in ("directory", "sticky directory"):
        return ('directory', file_output)
    elif file_output in ("block special", "character special"):
        return ('other', file_output)
    elif file_output.startswith("symbolic link to "):
        return ('symlink', file_output)
    else:
        return ('file', file_output)


def get_path_type(node, path):
    """
    Returns (TYPE, DESC) where TYPE is one of:

        'directory', 'file', 'nonexistent', 'other, 'symlink'

    and DESC is the output of the 'file' command line utility.
    """
    result = node.run("file -h {}".format(quote(path)), may_fail=True)
    if result.return_code != 0:
        return ('nonexistent', "")
    file_output = result.stdout.split(":")[1].strip()
    return _parse_file_output(file_output)
