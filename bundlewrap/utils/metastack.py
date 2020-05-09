from ..metadata import validate_metadata
from .dicts import _Atomic, freeze_object


def _dict_has_path(layer, path):
    current = layer
    for element in path.split('/'):
        if not isinstance(current, dict) or element not in current:
            return False, None
        current = current[element]
    return True, current


def _merge_layers(base, update):
    merged = base.copy()

    for key, value in update.items():
        if key in base and isinstance(base[key], _Atomic) and isinstance(value, _Atomic):
            raise MetastackTypeConflict('atomics on two levels for the same key {}'.format(key))

        if key not in base:
            merged[key] = value
        else:
            base_atomic = isinstance(base[key], _Atomic)
            value_atomic = isinstance(value, _Atomic)

            if isinstance(base[key], dict) and isinstance(value, dict):
                # XXX Feel free to optimize these at a later stage.
                if base_atomic:
                    pass
                elif value_atomic:
                    merged[key] = value
                else:
                    merged[key] = _merge_layers(base[key], value)
            elif (
                isinstance(base[key], list) and
                (
                    isinstance(value, list) or
                    isinstance(value, set) or
                    isinstance(value, tuple)
                )
            ):
                if base_atomic:
                    pass
                elif value_atomic:
                    merged[key] = value
                else:
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
                if base_atomic:
                    pass
                elif value_atomic:
                    merged[key] = value
                else:
                    merged[key] = base[key] + tuple(value)
            elif (
                isinstance(base[key], set) and
                (
                    isinstance(value, list) or
                    isinstance(value, set) or
                    isinstance(value, tuple)
                )
            ):
                if base_atomic:
                    pass
                elif value_atomic:
                    merged[key] = value
                else:
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


class Metastack:
    def __init__(self):
        # We rely heavily on insertion order in this dict.
        self._layers = {}

    def get(self, path, default, use_default=True):
        result = None
        undef = True

        for layer in self._layers.values():
            exists, value = _dict_has_path(layer, path)
            if exists:
                if undef:
                    # First time we see anything.
                    result = {'data': value}
                    undef = False
                else:
                    result = _merge_layers(result, {'data': value})

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

    def _as_dict(self):
        final_dict = {}

        for layer in self._layers.values():
            final_dict = _merge_layers(final_dict, layer)

        return final_dict

    def _as_blame(self):
        # TODO
        raise NotImplementedError

    def _set_layer(self, identifier, new_layer):
        # Marked with an underscore because only the internal metadata
        # reactor routing is supposed to call this method.
        validate_metadata(new_layer)
        changed = self._layers.get(identifier, {}) != new_layer
        self._layers[identifier] = new_layer
        return changed


class MetastackKeyError(Exception):
    pass


class MetastackTypeConflict(Exception):
    pass
