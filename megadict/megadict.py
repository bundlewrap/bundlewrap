from functools import wraps

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

    def __repr__(self):
        return f"""<Layer {repr({
            'callbacks': self.callbacks,
            'values': self.values,
        })}>"""


def takes_path(f):
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if args:
            path = args[0]
            if isinstance(path, str):
                if path:
                    args[0] = tuple(path.split("/"))
                else:
                    args[0] = ()
        else:
            args = [()]
        return f(self, *args, **kwargs)
    return wrapper


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
        return value1 | value2
    elif value1 is Undefined:
        return value2
    elif value2 is Undefined:
        return value1
    else:
        raise ValueError(f"cannot merge {type(value1)} {repr(value1)} and {type(value2)} {repr(value2)}")


class MegaDictNode:
    __slots__ = (
        'child_nodes',
        'layers',
        'key',
        'parent',
        'root',
    )

    def __init__(self, key=Undefined, parent=None, root=None):
        self.child_nodes = {}
        self.layers = {}
        self.key = key
        self.parent = parent
        self.root = root or self

    def _add(self, data, layer=0, source='unknown'):
        """
        This distributes the data provided by a callback to the proper
        nodes.
        """
        self._ensure_layer(layer)
        if isinstance(data, dict) and not isinstance(data, _Atomic):
            self.layers[layer].values[source] = {}
            for key, value in data.items():
                child_node = self._ensure_path((key,))
                self.layers[layer].values[source][key] = child_node
                child_node._add(value, layer=layer, source=source)
        else:
            self.layers[layer].values[source] = data

    def _ensure_layer(self, index):
        if index not in self.layers:
            self.layers[index] = Layer()
        if self.root != self:
            # we must collect all layers at the root, so nodes don't
            # have to do long searches to find out which layers might
            # exist on their parent nodes
            self.root._ensure_layer(index)

    def _ensure_path(self, path):
        if path:
            key = path[0]
            if key not in self.child_nodes:
                self.child_nodes[key] = MegaDictNode(key=key, parent=self, root=self.root)
            return self.child_nodes[key]._ensure_path(path[1:])
        else:
            return self

    @takes_path
    def add_callback_for_path(self, path, callback):
        if path:
            self._ensure_path((path[0],))
            self.child_nodes[path[0]].add_callback_for_path(path[1:], callback)
        else:
            self._ensure_layer(callback.layer)
            self.layers[callback.layer].callbacks.add(callback)

    @takes_path
    def get(self, path):
        value = self.get_node(path).value
        if value is Undefined:
            if path:
                raise KeyError(path)
            else:
                return {}
        else:
            return value

    @takes_path
    def get_node(self, path):
        if path:
            return self.child_nodes[path[0]].get_node(path[1:])
        else:
            return self

    @takes_path
    def keys(self, path):
        """
        Provides the keys for the dict at the given path without going
        through the trouble of assembling the values.
        """
        if path:
            return self.get_node(path).keys()

        value, blame = self._value_and_blame(resolve_child_nodes=False)

        if not isinstance(value, dict):
            raise ValueError(f"{self.path} is not a dict")

        return value.keys()

    @property
    def value(self):
        return self._value_and_blame()[0]

    @property
    def value_and_blame(self):
        return self._value_and_blame()

    def _run_callbacks_for_layer(self, layer_index):
        try:
            layer = self.layers[layer_index]
        except KeyError:
            pass
        else:
            for callback in layer.callbacks:
                if callback.has_run:
                    continue
                else:
                    callback.run()
        if self.parent:
            self.parent._run_callbacks_for_layer(layer_index)

    def _value_and_blame(self, resolve_child_nodes=True, only_layers=None):
        candidate = Undefined
        candidate_sources = set()
        visited_layers = []
        # It's important we iterate over *all* layers here, even if we
        # don't have them on the current node. If we didn't,
        # _run_callbacks_for_layer() might miss a higher layer on a
        # parent node.
        for layer_index in sorted(self.root.layers.keys()):
            if only_layers is not None and layer_index not in only_layers:
                continue
            visited_layers.append(layer_index)
            self._run_callbacks_for_layer(layer_index)

            try:
                layer = self.layers[layer_index]
            except KeyError:
                continue

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
                # no need to look at lower layers for this node
                break

        if candidate is Undefined and self.child_nodes:
            candidate = self.child_nodes.copy()

        if isinstance(candidate, dict) and not isinstance(candidate, _Atomic):
            if resolve_child_nodes:
                result = {}
                result_blame = set()
                for key, child_node in candidate.items():
                    value, blame = child_node.value_and_blame
                    if value is not Undefined:
                        result[key] = value
                        result_blame.update(blame)
                candidate = result
                candidate_sources = result_blame
        elif candidate is not Undefined:
            for key, child_node in self.child_nodes.items():
                child_value, child_blame = child_node._value_and_blame(only_layers=visited_layers)
                if child_value is not Undefined:
                    raise ValueError(f"conflict at {self.path} between {candidate_sources} and {child_blame}: {repr(candidate)} prevents merge of {repr(child_value)}")

        return candidate, candidate_sources

    @property
    def path(self):
        if self.key is Undefined:
            return ()
        else:
            return self.parent.path + (self.key,)


class MegaDictCallback:
    __slots__ = (
        'megadict',
        'identifier',
        'layer',
        'callback_func',
        'has_run',
    )

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
        self.megadict._add(result, layer=self.layer, source=self.identifier)
