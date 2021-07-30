from collections import defaultdict, Counter
from contextlib import suppress
from os import environ
from threading import RLock
from traceback import TracebackException

from .exceptions import MetadataPersistentKeyError
from .metadata import DoNotRunAgain
from .node import _flatten_group_hierarchy
from .utils import list_starts_with, randomize_order, NO_DEFAULT
from .utils.dicts import extra_paths_in_dict
from .utils.ui import io, QUIT_EVENT
from .utils.metastack import Metastack
from .utils.text import bold, mark_for_translation as _, red


MAX_METADATA_ITERATIONS = int(environ.get("BW_MAX_METADATA_ITERATIONS", "1000"))


class ReactorTree:
    def __init__(self, path_location=None):
        self._path_location = path_location
        self._children = {}
        self._reactors = set()

    def add(self, reactor, path):
        if path:
            self._children.setdefault(
                path[0],
                ReactorTree(path_location=path[0]),
            ).add(reactor, path[1:])
        else:
            self._reactors.add(reactor)

    def reactors_for(self, path=None):
        yield from self._reactors
        if path:
            try:
                child = self._children[path[0]]
            except KeyError:
                pass
            else:
                yield from child.reactors_for(path[1:])
        else:
            # yield entire subtree
            for child in self._children.values():
                yield from child.reactors_for()


class PathSet:
    """
    Collects metadata paths and stores only the highest levels ones.

    >>> s = PathSet()
    >>> s.add(("foo", "bar"))
    >>> s.add(("foo",))
    >>> s
    {"foo"}
    """

    def __init__(self, paths=tuple()):
        self._covers_cache = {}
        self._paths = set()
        for path in paths:
            self.add(path)

    def __iter__(self):
        for path in self._paths:
            yield path

    def __len__(self):
        return len(self._paths)

    def __repr__(self):
        return "<PathSet: {}>".format(repr(self._paths))

    def add(self, new_path):
        if self.covers(new_path):
            return False
        for existing_path in self._paths.copy():
            if list_starts_with(existing_path, new_path):
                self._paths.remove(existing_path)
        self._covers_cache = {}
        self._paths.add(new_path)
        return True

    def covers(self, candidate_path):
        """
        Returns True if the given path is already included.
        """
        try:
            return self._covers_cache[candidate_path]
        except KeyError:
            result = False
            for existing_path in self._paths:
                if list_starts_with(candidate_path, existing_path):
                    result = True
                    break
            self._covers_cache[candidate_path] = result
            return result


class NodeMetadataProxy:
    def __init__(self, metagen, node):
        self._metagen = metagen
        self._node = node
        self._metastack = Metastack()

    def __contains__(self, key):
        try:
            self.get(key, _backwards_compatibility_default=False)
        except KeyError:
            return False
        else:
            return True

    def __getitem__(self, key):
        return self.get((key,), _backwards_compatibility_default=False)

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

    def get(self, path, default=NO_DEFAULT, _backwards_compatibility_default=True):
        if (
            default == NO_DEFAULT and
            _backwards_compatibility_default and
            not self._metagen._in_a_reactor and
            "/" not in path
        ):
            # make node.metadata.get('foo') work as if it was still a dict
            # TODO remove in 5.0
            default = None
        if not isinstance(path, (tuple, list)):
            path = tuple(path.split("/"))

        if self._metagen._in_a_reactor and self._metagen._record_reactor_call_graph:
            for provided_path in self._metagen._current_reactor_provides:
                self._metagen._reactor_call_graph.add((
                    (self._metagen._current_reactor[0], provided_path),
                    (self._node.name, path),
                    self._metagen._current_reactor,
                ))

        with self._metagen._node_metadata_lock:
            # The lock is required because there are several thread-unsafe things going on here:
            #
            #   self._metagen._current_reactor_newly_requested_paths
            #   self._metagen._build_node_metadata
            #   self._metastack
            #
            # It needs to be an RLock because this method will be recursively
            # called from _build_node_metadata (when reactors call node.metadata.get()).
            if self._node not in self._metagen._relevant_nodes:
                self._metagen._initialize_node(self._node)
            if self._metagen._in_a_reactor:
                if self._metagen._reactors[self._metagen._current_reactor]['requested_paths'].add(
                    (self._node.name,) + path
                ):
                    self._metagen._current_reactor_newly_requested_paths.add(
                        (self._node.name,) + path
                    )
            else:
                io.debug(f"metagen triggered by request for {path} on {self._node.name}")
                self._metagen._trigger_reactors_for_path(
                    self._node.name,
                    path,
                    f"initial request for {path}",
                )
                with io.job(bold(_("building metadata..."))):
                    self._metagen._build_node_metadata(self._node)

            try:
                return self._metastack.get(path)
            except KeyError:
                if default != NO_DEFAULT:
                    return default
                else:
                    if self._metagen._in_a_reactor:
                        self._metagen._reactors[
                            self._metagen._current_reactor
                        ]['raised_keyerror_for'] = (self._node.name, path)
                    raise

    def items(self):
        return self.get(tuple()).items()

    def keys(self):
        return self.get(tuple()).keys()

    def values(self):
        return self.get(tuple()).values()


class MetadataGenerator:
    def __init__(self):
        # node.metadata calls these
        self._node_metadata_proxies = {}
        # metadata access is multi-threaded, but generation can't be
        self._node_metadata_lock = RLock()
        # guard against infinite loops
        self.__iterations = 0
        # reactors that raised KeyErrors (and which ones)
        self.__keyerrors = {}
        # all nodes involved with currently requested metadata
        self._relevant_nodes = set()
        # keep track of reactors and their dependencies
        self._reactors = {}
        # maps provided paths to their reactors
        self._provides_tree = ReactorTree()
        # how often we called reactors
        self.__reactors_run = 0
        # how often each reactor changed
        self._reactor_changes = defaultdict(int)
        # bw plot reactors
        self._reactor_call_graph = set()
        # are we currently executing a reactor?
        self._in_a_reactor = False
        # all new paths not requested before by the current reactor
        self._current_reactor_newly_requested_paths = set()
        # should reactor return values be checked against their declared keys?
        self._verify_reactor_provides = False
        # should we collect information for `bw plot reactors`?
        self._record_reactor_call_graph = False

    def _metadata_proxy_for_node(self, node_name):
        if node_name not in self._node_metadata_proxies:
            self._node_metadata_proxies[node_name] = \
                NodeMetadataProxy(self, self.get_node(node_name))
        return self._node_metadata_proxies[node_name]

    def _build_node_metadata(self, initial_node_name):
        while not QUIT_EVENT.is_set():
            io.debug("starting reactor run")
            any_reactor_ran, only_keyerrors = self.__run_reactors()
            if not any_reactor_ran:
                io.debug("reactor run completed, no reactors ran")
                # TODO maybe proxy._metastack.cache_partition(1) for COMPLETE nodes
                break
            elif only_keyerrors:
                io.debug("reactor run completed, all threw KeyErrors")
                break
            io.debug("reactor run completed, rerunning relevant reactors")

        if self.__keyerrors and not QUIT_EVENT.is_set():
            msg = _(
                "These metadata reactors raised a KeyError "
                "even after all other reactors were done:"
            )
            for source, exc in sorted(self.__keyerrors.items()):
                node_name, reactor = source
                msg += f"\n\n  {node_name} {reactor}\n\n"
                for line in TracebackException.from_exception(exc).format():
                    msg += "    " + line
            raise MetadataPersistentKeyError(msg)

        io.debug("metadata generation finished")

    def _initialize_node(self, node):
        io.debug(f"initializing metadata for {node.name}")

        with io.job(_("{}  assembling static metadata").format(bold(node.name))):
            # randomize order to increase chance of exposing clashing defaults
            for defaults_name, defaults in randomize_order(node.metadata_defaults):
                node.metadata._metastack.set_layer(
                    2,
                    defaults_name,
                    defaults,
                )
            node.metadata._metastack.cache_partition(2)

            group_order = _flatten_group_hierarchy(node.groups)
            for group_name in group_order:
                node.metadata._metastack.set_layer(
                    0,
                    "group:{}".format(group_name),
                    self.get_group(group_name)._attributes.get('metadata', {}),
                )

            node.metadata._metastack.set_layer(
                0,
                "node:{}".format(node.name),
                node._attributes.get('metadata', {}),
            )
            node.metadata._metastack.cache_partition(0)

        with io.job(_("{}  preparing metadata reactors").format(bold(node.name))):
            io.debug(f"adding {len(list(node.metadata_reactors))} reactors for {node.name}")
            for reactor_name, reactor in randomize_order(node.metadata_reactors):
                # randomizing insertion order increases the chance of
                # exposing weird reactors that depend on execution order
                self._reactors[(node.name, reactor_name)] = {
                    'raised_keyerror_for': None,
                    'raised_donotrunagain': False,
                    'reactor': reactor,
                    'requested_paths': PathSet(),
                    'trigger_on_change': set(),
                    'triggered_by': set(),
                }
                for path in getattr(reactor, '_provides', (tuple(),)):
                    self._provides_tree.add(
                        (node.name, reactor_name),
                        (node.name,) + path,
                    )

        self._relevant_nodes.add(node)

    def _trigger_reactors_for_path(self, node_name, path, source):
        for reactor in self._provides_tree.reactors_for((node_name,) + path):
            if reactor != source:  # we don't want to trigger ourselves
                io.debug(f"{source} triggers {reactor}")
                self._reactors[reactor]['triggered_by'].add(source)

    def __check_iteration_count(self):
        self.__iterations += 1
        if self.__iterations > MAX_METADATA_ITERATIONS:
            top_changers = Counter(self._reactor_changes).most_common(25)
            msg = _(
                "MAX_METADATA_ITERATIONS({m}) exceeded, "
                "likely an infinite loop between flip-flopping metadata reactors.\n"
                "These are the reactors that changed most often:\n\n"
            ).format(m=MAX_METADATA_ITERATIONS)
            for reactor, count in top_changers:
                msg += f"  {count}\t{reactor[0]}\t{reactor[1]}\n"
            raise RuntimeError(msg)

    def __run_reactors(self):
        self.__check_iteration_count()
        any_reactor_ran = False
        only_keyerrors = True
        for with_keyerrors in (False, True):
            # make sure we run reactors that raised KeyError *after*
            # those that didn't to increase the chance of finding what
            # those KeyErrors were looking for
            for reactor_id, reactor_dict in list(self._reactors.items()):
                node_name, reactor_name = reactor_id
                if reactor_dict['raised_donotrunagain']:
                    continue
                if reactor_dict['raised_keyerror_for']:
                    if not with_keyerrors:
                        continue
                    io.debug(
                        f"running reactor {reactor_id} because "
                        f"it previously raised a KeyError for: {reactor_dict['raised_keyerror_for']}"
                    )
                elif reactor_dict['triggered_by']:
                    if with_keyerrors:
                        continue
                    io.debug(
                        f"running reactor {reactor_id} because "
                        f"it was triggered by: {reactor_dict['triggered_by']}"
                    )
                else:
                    continue
                any_reactor_ran = True
                with io.job(_("{node}  running {reactor}...").format(
                    node=bold(node_name),
                    reactor=bold(reactor_name),
                )):
                    reactor_changed_return_value = self.__run_reactor(
                        self.get_node(node_name),
                        reactor_name,
                        reactor_dict['reactor'],
                    )
                if reactor_changed_return_value:
                    reactor_id = (node_name, reactor_name)
                    for triggered_reactor in self._reactors[reactor_id]['trigger_on_change']:
                        io.debug(f"rerun of {triggered_reactor} triggered by {reactor_id}")
                        self._reactors[triggered_reactor]['triggered_by'].add(reactor_id)
                if not self._reactors[(node_name, reactor_name)]['raised_keyerror_for']:
                    only_keyerrors = False
        return any_reactor_ran, only_keyerrors

    def __run_reactor(self, node, reactor_name, reactor):

        self.__reactors_run += 1
        # make sure the reactor doesn't react to its own output
        old_metadata = node.metadata._metastack.pop_layer(1, reactor_name)
        self._in_a_reactor = True
        self._current_reactor = (node.name, reactor_name)
        self._current_reactor_provides = getattr(reactor, '_provides', (("/",),))  # used in .get()
        self._current_reactor_newly_requested_paths = set()
        try:
            new_metadata = reactor(node.metadata)
        except KeyError as exc:
            if not self._reactors[self._current_reactor]['raised_keyerror_for']:
                self._reactors[self._current_reactor]['raised_keyerror_for'] = 'UNKNOWN'
            self.__keyerrors[self._current_reactor] = exc
            io.debug(
                f"{self._current_reactor} raised KeyError: "
                f"{self._reactors[self._current_reactor]['raised_keyerror_for']}"
            )
            return False
        except DoNotRunAgain:
            self._reactors[self._current_reactor]['raised_donotrunagain'] = True
            # clear any previously stored exception
            with suppress(KeyError):
                del self.__keyerrors[self._current_reactor]
            self._current_reactor_newly_requested_paths.clear()
            io.debug(f"{self._current_reactor} raised DoNotRunAgain")
            return False
        except Exception as exc:
            io.stderr(_(
                "{x} Exception while executing metadata reactor "
                "{metaproc} for node {node}:"
            ).format(
                x=red("!!!"),
                metaproc=reactor_name,
                node=node.name,
            ))
            raise exc
        finally:
            self._in_a_reactor = False
            self._reactors[self._current_reactor]['triggered_by'].clear()
            for path in self._current_reactor_newly_requested_paths:
                for reactor in self._provides_tree.reactors_for(path):
                    # make sure these newly required reactors run at least once
                    io.debug(f"triggering {reactor} as new dependency of {self._current_reactor}")
                    self._reactors[reactor]['trigger_on_change'].add(self._current_reactor)
                    self._reactors[reactor]['triggered_by'].add(self._current_reactor)

        # reactor terminated normally, clear any previously stored exception
        self._reactors[self._current_reactor]['raised_keyerror_for'] = None
        with suppress(KeyError):
            del self.__keyerrors[self._current_reactor]

        if self._verify_reactor_provides and getattr(reactor, '_provides', None):
            extra_paths = extra_paths_in_dict(new_metadata, reactor._provides)
            if extra_paths:
                raise ValueError(_(
                    "{reactor_name} on {node_name} returned the following key paths, "
                    "but didn't declare them with @metadata_reactor.provides():\n"
                    "{paths}"
                ).format(
                    node_name=node.name,
                    reactor_name=reactor_name,
                    paths="\n".join(["/".join(path) for path in sorted(extra_paths)]),
                ))

        try:
            node.metadata._metastack.set_layer(
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
                node=node.name,
            ))
            raise exc

        changed = old_metadata != new_metadata
        if changed:
            self._reactor_changes[self._current_reactor] += 1

        io.debug(f"{self._current_reactor} returned changed result: {changed}")

        return changed
