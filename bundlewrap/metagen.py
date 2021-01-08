from .node import _flatten_group_hierarchy
from .utils import list_starts_with, randomize_order, NO_DEFAULT
from .utils.dicts import extra_paths_in_dict
from .utils.ui import io, QUIT_EVENT
from .utils.metastack import Metastack
from .utils.text import bold, mark_for_translation as _, red


def reactors_for_path(available_reactors, path):
    """
    Returns only those available_reactors that might affect the path.
    """
    for name, reactor in available_reactors:
        for provided_path in reactor._provides:
            minlen = min(len(provided_path), len(path))
            for i in range(minlen):
                if not (
                    provided_path[i] is None or
                    path[i] is None or
                    provided_path[i] == path[i]
                ):
                    break
            else:
                yield name, reactor
                break


class NodeMetadataProxy:
    def __init__(self, metagen, node):
        self._metagen = metagen
        self._node = node
        self._metastack = Metastack()
        self._available_reactors = set(node.metadata_reactors)
        self._prepare_static_metadata()

    def __getitem__(self, key):
        return self.get((key,))

    def __iter__(self):
        for key, value in self.get(tuple()).items():
            yield key, value

    @property
    def blame(self):
        if self._metagen._in_a_reactor:
            raise RuntimeError("cannot call node.metadata.blame from a reactor")
        else:
            return self._metastack.as_blame()

    @property
    def stack(self):
        if self._metagen._in_a_reactor:
            raise RuntimeError("cannot call node.metadata.stack from a reactor")
        else:
            return self._metastack

    def get(self, path, default=NO_DEFAULT):
        if not isinstance(path, (tuple, list)):
            path = tuple(path.split("/"))

        was_already_in_a_reactor = self._metagen._in_a_reactor
        self._metagen._in_a_reactor = True
        if was_already_in_a_reactor:
            self._run_reactors_for_path(path)
        else:
            with self._metagen._node_metadata_lock:
                self._run_reactors_for_path(path)
            self._metagen._in_a_reactor = False

        try:
            return self._metastack.get(path)
        except KeyError:
            if default != NO_DEFAULT:
                return default
            else:
                raise

    def _run_reactors_for_path(self, path):
        for reactor_name, reactor in tuple(reactors_for_path(self._available_reactors, path)):
            try:
                self._available_reactors.remove((reactor_name, reactor))
            except KeyError:
                # a reactor called from a previous iteration in this loop
                # might already have executed this reactor
                continue
            else:
                self._run_reactor(reactor_name, reactor)

    def _prepare_static_metadata(self):
        # randomize order to increase chance of exposing clashing defaults
        for defaults_name, defaults in randomize_order(self._node.metadata_defaults):
            self._metastack.set_layer(
                2,
                defaults_name,
                defaults,
            )
        self._metastack.cache_partition(2)

        group_order = _flatten_group_hierarchy(self._node.groups)
        for group_name in group_order:
            self._metastack.set_layer(
                0,
                "group:{}".format(group_name),
                self._metagen.get_group(group_name)._attributes.get('metadata', {}),
            )

        self._metastack.set_layer(
            0,
            "node:{}".format(self._node.name),
            self._node._attributes.get('metadata', {}),
        )
        self._metastack.cache_partition(0)

    def _run_reactor(self, reactor_name, reactor):
        try:
            new_metadata = reactor(self._node.metadata)  # TODO remove param
        except Exception as exc:
            io.stderr(_(
                "{x} Exception while executing metadata reactor "
                "{metaproc} for node {node}:"
            ).format(
                x=red("!!!"),
                metaproc=reactor_name,
                node=self._node.name,
            ))
            raise exc

        if self._metagen._verify_reactor_provides:  # TODO do always?
            extra_paths = extra_paths_in_dict(new_metadata, reactor._provides)
            if extra_paths:
                raise ValueError(_(
                    "{reactor_name} on {node_name} returned the following key paths, "
                    "but didn't declare them with @metadata_reactor.provides():\n"
                    "{paths}"
                ).format(
                    node_name=self._node.name,
                    reactor_name=reactor_name,
                    paths="\n".join(["/".join(path) for path in sorted(extra_paths)]),
                ))

        try:
            self._metastack.set_layer(
                1,
                reactor_name,
                new_metadata,
            )
        except TypeError as exc:
            # TODO catch validation errors better
            io.stderr(_(
                "{x} Exception after executing metadata reactor "
                "{metaproc} for node {node}:"
            ).format(
                x=red("!!!"),
                metaproc=reactor_name,
                node=self._node.name,
            ))
            raise exc


class MetadataGenerator:
    # are we currently executing a reactor?
    _in_a_reactor = False
    # should reactor return values be checked against their declared keys?
    _verify_reactor_provides = False

    def _metadata_proxy_for_node(self, node_name):
        if node_name not in self._node_metadata_proxies:
            self._node_metadata_proxies[node_name] = NodeMetadataProxy(self, self.get_node(node_name))
        return self._node_metadata_proxies[node_name]
