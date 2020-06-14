from collections import OrderedDict
from sys import version_info

from ..metadata import deepcopy_metadata, validate_metadata, value_at_key_path
from . import NO_DEFAULT
from .dicts import map_dict_keys, merge_dict


class Metastack:
    """
    Holds a number of metadata layers. When laid on top of one another,
    these layers form complete metadata for a node. Each layer comes
    from one particular source of metadata: a bundle default, a group,
    the node itself, or a metadata reactor. Metadata reactors are unique
    in their ability to revise their own layer each time they are run.
    """
    def __init__(self):
        # We rely heavily on insertion order in this dict.
        if version_info < (3, 7):
            self._layers = OrderedDict()
        else:
            self._layers = {}

    def get(self, path, default=NO_DEFAULT):
        """
        Get the value at the given path, merging all layers together.

        Path may either be string like

            'foo/bar'

        accessing the 'bar' key in the dict at the 'foo' key
        or a tuple like

            ('fo/o', 'bar')

        accessing the 'bar' key in the dict at the 'fo/o' key.
        """
        if not isinstance(path, (tuple, list)):
            path = path.split('/')

        result = None
        undef = True

        for layer in self._layers.values():
            try:
                value = value_at_key_path(layer, path)
            except KeyError:
                pass
            else:
                if undef:
                    # First time we see anything.
                    result = {'data': value}
                    undef = False
                else:
                    result = merge_dict(result, {'data': value})

        if undef:
            if default != NO_DEFAULT:
                return default
            else:
                raise KeyError('/'.join(path))
        else:
            return deepcopy_metadata(result['data'])

    def _as_dict(self):
        final_dict = {}

        for layer in self._layers.values():
            final_dict = merge_dict(final_dict, layer)

        return final_dict

    def _as_blame(self):
        keymap = map_dict_keys(self._as_dict())
        blame = {}
        for path in keymap:
            for identifier, layer in self._layers.items():
                try:
                    value_at_key_path(layer, path)
                except KeyError:
                    pass
                else:
                    blame.setdefault(path, []).append(identifier)
        return blame

    def _set_layer(self, identifier, new_layer):
        # Marked with an underscore because only the internal metadata
        # reactor routing is supposed to call this method.
        validate_metadata(new_layer)
        changed = self._layers.get(identifier, {}) != new_layer
        self._layers[identifier] = new_layer
        return changed
