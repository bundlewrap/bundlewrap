from collections import namedtuple
from contextlib import suppress

from bundlewrap.utils.dicts import _Atomic


class Undefined:
    pass


class Layer:
    __slots__ = (
        'callbacks',
        'values',
    )

    def __init__(self):
        self.callbacks = set()
        self.values = {}


def merge(value1, value2):
    if isinstance(value1, _Atomic) or isinstance(value2, _Atomic):
        raise ValueError(f"atomic() forbids merge of {type(value1)} {repr(value1)} and {type(value2)} {repr(value2)}")
    elif isinstance(value1, dict) and isinstance(value2, dict):
        result = value1.copy()
        for key, value in value2.items():
            if key in result and result[key] != value:
                raise ValueError(f"conflicting keys in {repr(value1)} and {repr(value2)}")
            else:
                result[key] = value
        return result
    elif isinstance(value1, set) and isinstance(value2, set):
        return value1 & value2
    elif value1 is Undefined:
        return value2
    elif value2 is Undefined:
        return value1
    else:
        raise ValueError(f"cannot merge {type(value1)} {repr(value1)} and {type(value2)} {repr(value2)}")


class MegaDictNode:
    def __init__(self, key=Undefined, parent=None, root=None):
        self.child_nodes = {}
        self.layers = {}
        self.key = key
        self.parent = parent
        self.root = root

    def add(self, data, layer=0, source='unknown'):
        self.ensure_layer(layer)
        if isinstance(data, dict) and not isinstance(data, _Atomic):
            self.layers[layer].values[source] = {}
            for key, value in data.items():
                child_node = self.ensure_path((key,))
                self.layers[layer].values[source][key] = child_node
                child_node.add(value, layer=layer, source=source)
        else:
            self.layers[layer].values[source] = data

    def ensure_layer(self, index):
        if index not in self.layers:
            self.layers[index] = Layer()

    def ensure_path(self, path):
        if path:
            key = path[0]
            if key not in self.child_nodes:
                self.child_nodes[key] = MegaDictNode(key=key, parent=self, root=self.root)
            return self.child_nodes[key].ensure_path(path[1:])
        else:
            return self

    def add_callback_for_path(self, path, callback):
        if path:
            self.ensure_path((path[0],))
            self.child_nodes[path[0]].add_callback_for_path(path[1:], callback)
        else:
            self.ensure_layer(callback.layer)
            self.layers[callback.layer].callbacks.add(callback)

    def remove(self, layer, source):
        with suppress(KeyError):
            del self.layers[layer].values[source]

        for child_node in self.child_nodes.values():
            child_node.remove(layer, source)

    def get(self, path=()):
        value = self.get_node(path).value
        if value is Undefined:
            if path:
                raise KeyError(path)
            else:
                return {}
        else:
            return value

    def get_node(self, path):
        if path:
            return self.child_nodes[path[0]].get_node(path[1:])
        else:
            return self

    def make_nodes(self, path):
        child_identifier = path[0]
        try:
            child_node = self.child_nodes[child_identifier]
        except KeyError:
            child_node = MegaDictNode(child_identifier)
            self.child_nodes[child_identifier] = child_node
        yield from child_node.get_node(path[1:])

    @property
    def value(self):
        return self.value_and_blame[0]

    @property
    def value_and_blame(self):
        candidate = Undefined
        candidate_sources = set()
        for layer_index, layer in sorted(self.layers.items()):
            for callback in layer.callbacks:
                if callback.has_run:
                    continue
                else:
                    callback.run()

            for source, value in layer.values.items():
                if candidate is Undefined:
                    candidate = value
                    candidate_sources.add(source)
                    continue

                try:
                    candidate = merge(candidate, value)
                except ValueError as exc:
                    raise ValueError(f"conflict at {self.path} between {candidate_sources} and {source}: {exc}")
                else:
                    candidate_sources.add(source)

            if (
                candidate is not Undefined
                and (
                    not isinstance(candidate, (dict, set))
                    or isinstance(candidate, _Atomic)
                )
            ):
                # no need to look at lower layers
                return candidate, candidate_sources

        if isinstance(candidate, dict):
            result = {}
            for key, child_node in candidate.items():
                value = child_node.value
                if value is not Undefined:
                    result[key] = value
            return result, candidate_sources
        else:
            return candidate, candidate_sources

    @property
    def path(self):
        if self.key is Undefined:
            return ()
        else:
            return self.parent.path + (self.key,)


class MegaDictCallback:
    def __init__(self, megadict, identifier, layer, callback_func):
        self.megadict = megadict
        self.identifier = identifier
        self.layer = layer
        self.callback_func = callback_func
        self.has_run = False

    def run(self):
        self.has_run = True
        result = self.callback_func(self.megadict)
        del self.callback_func
        self.megadict.add(result, layer=self.layer, source=self.identifier)
