# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .dicts import merge_dict


class Metastack(object):
    def __init__(self, base={}):
        self._base = base
        self._layers = {}

    def get(self, path, default, use_default=True):
        result = None
        undef = True

        for layer in [self._base] + list(self._layers.values()):
            exists, value = self._dict_has_path(layer, path)
            if exists:
                if undef:
                    # First time we see anything.
                    result = {'data': value}
                    undef = False
                else:
                    result = merge_dict(result, {'data': value})

        if undef:
            if use_default:
                return default
            else:
                raise MetastackKeyError('Path {} not in metastack'.format(path))
        else:
            return result['data']

    def has(self, path):
        try:
            self.get(path, '<unused>', use_default=False)
        except MetastackKeyError:
            return False
        return True

    def _dict_has_path(self, layer, path):
        current = layer
        for element in path.split('/'):
            if not isinstance(current, dict) or element not in current:
                return False, None
            current = current[element]

        return True, current

    def _set_layer(self, identifier, new_layer):
        # Marked with an underscore because only the internal metadata
        # reactor routing is supposed to call this method.
        self._layers[identifier] = new_layer


class MetastackKeyError(Exception):
    pass
