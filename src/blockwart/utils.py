from imp import find_module, load_module
from os.path import basename, dirname


def import_module(path):
    """
    Imports the given file as a Python module.
    """
    mod_name = basename(path).split(".")[0]
    (f, pathname, description) = find_module(mod_name, [dirname(path)])
    return load_module(mod_name, f, pathname, description)


def mark_for_translation(s):
    return s
