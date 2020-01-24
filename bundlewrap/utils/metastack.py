# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .dicts import _Atomic, freeze_object


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
                    result = self._merge_layers(result, {'data': value})

        if undef:
            if use_default:
                return default
            else:
                raise MetastackKeyError('Path {} not in metastack'.format(path))
        else:
            return freeze_object(result['data'])

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

    def _merge_layers(self, base, update):
        merged = base.copy()

        for key, value in update.items():
            if isinstance(value, _Atomic):
                raise MetastackAtomicIllegal()

            if key not in base:
                merged[key] = value
            else:
                if isinstance(base[key], _Atomic):
                    pass
                elif isinstance(base[key], dict) and isinstance(value, dict):
                    merged[key] = self._merge_layers(base[key], value)
                elif (
                    isinstance(base[key], list) and
                    (
                        isinstance(value, list) or
                        isinstance(value, set) or
                        isinstance(value, tuple)
                    )
                ):
                    extended = base[key][:]
                    extended.extend(value)
                    merged[key] = extended
                elif (
                    isinstance(base[key], tuple) and
                    (
                        isinstance(value, list) or
                        isinstance(value, set) or
                        isinstance(value, tuple)
                    )
                ):
                    merged[key] = base[key] + tuple(value)
                elif (
                    isinstance(base[key], set) and
                    (
                        isinstance(value, list) or
                        isinstance(value, set) or
                        isinstance(value, tuple)
                    )
                ):
                    merged[key] = base[key].union(set(value))
                elif (
                    (
                        (isinstance(base[key], bool) and isinstance(value, bool)) or
                        (isinstance(base[key], bytes) and isinstance(value, bytes)) or
                        (isinstance(base[key], int) and isinstance(value, int)) or
                        (isinstance(base[key], str) and isinstance(value, str)) or
                        (base[key] is None and value is None)
                    )
                ):
                    merged[key] = value
                else:
                    raise MetastackTypeConflict()

        return merged

    def _set_layer(self, identifier, new_layer):
        # Marked with an underscore because only the internal metadata
        # reactor routing is supposed to call this method.
        self._layers[identifier] = new_layer


class MetastackAtomicIllegal(Exception):
    pass


class MetastackKeyError(Exception):
    pass


class MetastackTypeConflict(Exception):
    pass
