from functools import wraps

from bundlewrap.utils.dicts import _Atomic


class Undefined:
    pass


class Layer:
    __slots__ = (
        'callbacks',
        'links',
        'values',
    )

    def __init__(self):
        self.callbacks = set()
        self.links = set()
        self.values = {}

    def __repr__(self):
        return f"""<Layer {repr({
            'callbacks': self.callbacks,
            'links': self.links,
            'values': self.values,
        })}>"""


def unstring_path(path):
    if isinstance(path, str):
        if path:
            path = tuple(path.split("/"))
        else:
            path = ()
    return path


def takes_path(f):
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if args:
            path = unstring_path(args[0])
        else:
            path = ()
        return f(self, path, *args[1:], **kwargs)
    return wrapper


def merge(value1, value2):
    if isinstance(value1, _Atomic) or isinstance(value2, _Atomic):
        raise ValueError(
            f"atomic() forbids merge of {type(value1)} {repr(value1)} "
            f"and {type(value2)} {repr(value2)}"
        )
    elif isinstance(value1, dict) and isinstance(value2, dict):
        result = value1.copy()
        for key, value in value2.items():
            if key in result and result[key] is not Undefined:  # ignore same child node
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
        raise ValueError(
            f"cannot merge {type(value1)} {repr(value1)} and {type(value2)} {repr(value2)}"
        )


class MegaDictNode:
    __slots__ = (
        'callbacks_on_stack',
        'child_nodes',
        'layers',
        'key',
        'parent',
        'root',
    )

    def __init__(self, key=Undefined, parent=None, root=None):
        self.callbacks_on_stack = []
        self.child_nodes = {}
        self.layers = {}
        self.key = key
        self.parent = parent
        self.root = root or self

    def _add(self, data, layer, source):
        """
        This distributes the data provided by a callback to the proper
        nodes.
        """
        self._ensure_layer(layer)
        if isinstance(data, dict) and not isinstance(data, _Atomic):
            self.layers[layer].values[source] = {}
            for key, value in data.items():
                child_node = self._ensure_path((key,))
                self.layers[layer].values[source][key] = Undefined
                child_node._add(value, layer, source)
        else:
            self.layers[layer].values[source] = data

    def _remove(self, data, layer, source):
        """
        Undo for _add().
        """
        if isinstance(data, dict) and not isinstance(data, _Atomic):
            for key, value in data.items():
                child_node = self._ensure_path((key,))
                child_node._remove(value, layer, source)
        del self.layers[layer].values[source]

    def _ensure_layer(self, index):
        """
        Creates a new layer object if necessary and registers it at the
        root.
        """
        if index not in self.layers:
            self.layers[index] = Layer()
        if self.root != self:
            # we must collect all layers at the root, so nodes don't
            # have to do long searches to find out which layers might
            # exist on their parent nodes
            self.root._ensure_layer(index)
        return self.layers[index]

    def _ensure_path(self, path):
        """
        Creates new MegaDictNodes along the given path if needed.
        """
        if path:
            key = path[0]
            if key not in self.child_nodes:
                self.child_nodes[key] = MegaDictNode(key=key, parent=self, root=self.root)
            return self.child_nodes[key]._ensure_path(path[1:])
        else:
            return self

    def add_callback_for_paths(self, paths, callback_func, layer=0, source=None):
        if not source:
            source = repr(callback_func)
        callback = MegaDictCallback(self, layer, callback_func, source)
        for path in paths:
            path = unstring_path(path)
            self._add_callback_for_path(path, callback)

    def _add_callback_for_path(self, path, callback):
        if path:
            self._ensure_path((path[0],))
            self.child_nodes[path[0]]._add_callback_for_path(path[1:], callback)
        else:
            self._ensure_layer(callback.layer)
            self.layers[callback.layer].callbacks.add(callback)

    @takes_path
    def get(self, path, default=Undefined):
        value = self.get_node(path).value
        if value is Undefined:
            if path:
                if default is Undefined:
                    raise KeyError(path)
                else:
                    return default
            else:
                return {}
        else:
            return value

    @takes_path
    def get_node(self, path):
        if path:
            return self._ensure_path(path)
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

    def link(self, other_node, layer_index):
        self._ensure_layer(layer_index).links.add(other_node)

    @property
    def value(self):
        return self._value_and_blame()[0]

    @property
    def blame(self):
        return self._value_and_blame()[1]

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
                callback.run()
        if self.parent:
            # our parents might also provide relevant values
            self.parent._run_callbacks_for_layer(layer_index)

    def _value_and_blame_from_linked(self, path, layer_index):
        if self.parent:
            yield from self.parent._value_and_blame_from_linked((self.key,), layer_index)
        try:
            layer = self.layers[layer_index]
        except KeyError:
            pass
        else:
            for linked_node in layer.links:
                yield linked_node.get_node(path)._value_and_blame(resolve_child_nodes=False)

    def _value_and_blame(self, resolve_child_nodes=True, only_layers=None):
        value = Undefined
        blame = set()
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

            candidate_values_and_blame = []
            candidate_values_and_blame.extend(self._value_and_blame_from_linked((), layer_index))

            try:
                layer = self.layers[layer_index]
            except KeyError:
                pass
            else:
                for source, candidate_value in layer.values.items():
                    candidate_values_and_blame.append((candidate_value, {source}))

            for candidate_value, sources in candidate_values_and_blame:
                if value is Undefined:
                    value = candidate_value
                    blame.update(sources)
                    continue
                try:
                    value = merge(value, candidate_value)
                except ValueError as exc:
                    raise ValueError(
                        f"conflict at {self.path} between {blame} and {source}: {exc}"
                    )
                else:
                    blame.update(sources)

            if (
                value is not Undefined
                and (
                    not isinstance(value, (dict, set))
                    or isinstance(value, _Atomic)
                )
            ):
                # no need to look at lower layers for this node
                break

        if value is Undefined and self.child_nodes:
            value = {
                key: Undefined
                for key in self.child_nodes
            }

        if isinstance(value, dict) and not isinstance(value, _Atomic):
            # We were asked to provide a full dict for the current path,
            # so we need to recursively replace the child nodes in that
            # dict with their effective values.
            if resolve_child_nodes:
                result = {}
                result_blame = set()
                for key in value:
                    # key might not already exist as child node because
                    # it's from a linked layer
                    child_node = self.get_node((key,))
                    child_value, child_blame = child_node.value_and_blame
                    if child_value is not Undefined:
                        result[key] = child_value
                        result_blame.update(child_blame)
                value = result
                blame = result_blame
        elif value is not Undefined:
            # We have found a non-mergable value here, but still need
            # to make sure our children don't define a dict at the same
            # or a higher layer.
            for key, child_node in self.child_nodes.items():
                child_value, child_blame = child_node._value_and_blame(only_layers=visited_layers)
                if child_value is not Undefined:
                    raise ValueError(
                        f"conflict at {self.path} between {blame} and {child_blame}: "
                        f"{repr(value)} prevents merge of {repr(child_value)}"
                    )

        return value, blame

    @property
    def path(self):
        if self.key is Undefined:
            return ()
        else:
            return self.parent.path + (self.key,)


class MegaDictCallback:
    __slots__ = (
        '_megadict',
        'source',
        'layer',
        '_callback_func',
        'needs_to_run',
        'reentrant',
        'previous_result',
    )

    def __init__(self, megadict, layer, callback_func, source):
        self._megadict = megadict
        self.source = source
        self.layer = layer
        self._callback_func = callback_func
        self.needs_to_run = True
        self.reentrant = False
        self.previous_result = None

    def __repr__(self):
        return f"<MegaDictCallback '{self.source}' on layer {self.layer}>"

    def run(self):
        if not self.reentrant:
            try:
                index = self._megadict.callbacks_on_stack.index(self)
            except ValueError:
                pass
            else:
                # we're about to call ourselves again, let's not do that
                # and mark everything involved in the call loop as
                # reentrant instead
                for callback in self._megadict.callbacks_on_stack[index:]:
                    callback.reentrant = True
                    callback.needs_to_run = True
                return

        if self.needs_to_run:
            if not self.reentrant:
                self._megadict.callbacks_on_stack.append(self)
            result = self._callback_func(self._megadict)
            if not self.reentrant:
                self._megadict.callbacks_on_stack.remove(self)

            self.needs_to_run = False
            changed = result != self.previous_result

            if changed:
                if self.previous_result is not None:
                    self._megadict._remove(self.previous_result, self.layer, self.source)
                self.previous_result = result
                self._megadict._add(result, layer=self.layer, source=self.source)

                for callback in self._megadict.callbacks_on_stack:
                    if callback.reentrant and callback != self:
                        callback.needs_to_run = True
                # we need a second loop here because one call to .run()
                # may cause other callbacks to run as well and we don't
                # want to mark them as needs_to_run again
                for callback in self._megadict.callbacks_on_stack:
                    if callback.reentrant and callback != self:
                        callback.run()




# TODO:
# * enforce provides
# * enforce adding new callbacks from callbacks only within existing provides




#@provides('nginx/vhosts')
#def foo(m):
#    result = {'nginx': {'vhosts': {}}}
#    for key, value in m.get('nginx/vhosts').items():
#        if value.get('moo') == 5 and '_stats' not in key:
#            result['nginx']['vhosts'][key + '_stats'] = {}
#    return result
#
#
#@provides('nginx/vhosts')
#def bar(m):
#    result = {'nginx': {'vhosts': {}}}
#    for key in m.iter('nginx/vhosts'):
#        result['nginx']['vhosts'][key]['moo'] = 5
#    return result
#
#
#@provides('nginx/vhosts')
#def baz(m):
#    result = {'nginx': {'vhosts': {}}}
#    for key in m.iter('nginx/vhosts'):
#        result['nginx']['vhosts'][key]['blubb'] = m.get(f'nginx/vhosts/{key}/moo')
#    return result
#
#
#
#
#
#
#@provides('dns/records')
#def foo(m):
#    result = {'dns': {'records': {}}}
#    for key in m.iter('dns/records'):
#        result['dns']['records'][key + '.local'] = {'AAAA': '127.0.0.1'}
#    return result
#
#
#@provides('dns/records')
#def bar(m):
#    result = {'dns': {'records': {}}}
#    for key in m.iter('dns/records'):
#        result['dns']['records'][key]['ttl'] = 5
#    return result
#
#
#@provides('dns/records')
#def baz(m):
#    return {
#        'dns': {
#            'records': {
#                m.get('mailserver_domain'): {
#                    'AAAA': m.get('mailserver_ip'),
#                },
#            },
#        },
#    }
#
#
#
#@provides('foo')
#def foo1(m):
#    return {'foo': {'value': m.get('bar', None), 'hint': 47}}
#
#
#@provides('bar')
#def bar1(m):
#    return {'bar': m.get('foo/hint', None)}
#
