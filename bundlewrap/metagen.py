from os import environ
from traceback import TracebackException

from .exceptions import MetadataPersistentKeyError
from .metadata import DoNotRunAgain
from .node import _flatten_group_hierarchy
from .utils import randomize_order
from .utils.ui import io, QUIT_EVENT
from .utils.metastack import Metastack
from .utils.text import bold, mark_for_translation as _, red


MAX_METADATA_ITERATIONS = int(environ.get("BW_MAX_METADATA_ITERATIONS", "5000"))


class MetadataGenerator:
    def __reset(self):
        # reactors that raise DoNotRunAgain
        self.__do_not_run_again = set()
        # reactors that raised KeyErrors (and which ones)
        self.__keyerrors = {}
        # a Metastack for every node
        self.__metastacks = {}
        # mapping each node to all nodes that depend on it
        self.__node_deps = {}
        # A node is 'stable' when all its reactors return unchanged
        # metadata, except for those reactors that look at other nodes.
        # This dict maps node names to True/False indicating stable status.
        self.__node_stable = {}
        # nodes we encountered as a dependency through partial_metadata,
        # but haven't run yet
        self.__nodes_that_never_ran = set()
        # nodes whose dependencies changed and that have to rerun their
        # reactors depending on those nodes
        self.__triggered_nodes = set()
        # nodes we already did initial processing on
        self.__nodes_that_ran_at_least_once = set()
        self.__reactors_run = 0
        # tracks which reactors on a node have look at other nodes
        # through partial_metadata
        self.__reactors_with_deps = {}

    def _metadata_for_node(self, node_name, partial=False, blame=False, stack=False):
        """
        Returns full or partial metadata for this node. This is the
        primary entrypoint accessed from node.[partial_]metadata.

        Partial metadata may only be requested from inside a metadata
        reactor.

        If necessary, this method will build complete metadata for this
        node and all related nodes. Related meaning nodes that this node
        depends on in one of its metadata reactors.
        """
        if partial:
            if node_name in self._node_metadata_complete:
                # We already completed metadata for this node, but partial must
                # return a Metastack, so we build a single-layered one just for
                # the interface.
                metastack = Metastack()
                metastack._set_layer(
                    0,
                    "flattened",
                    self._node_metadata_complete[node_name],
                )
                return metastack
            else:
                self.__partial_metadata_accessed_for.add(node_name)
                return self.__metastacks.setdefault(node_name, Metastack())

        if blame or stack:
            # cannot return cached result here, force rebuild
            try:
                del self._node_metadata_complete[node_name]
            except KeyError:
                pass

        try:
            return self._node_metadata_complete[node_name]
        except KeyError:
            pass

        # Different worker threads might request metadata at the same time.

        with self._node_metadata_lock:
            try:
                # maybe our metadata got completed while waiting for the lock
                return self._node_metadata_complete[node_name]
            except KeyError:
                pass

            self.__build_node_metadata(node_name)

            # now that we have completed all metadata for this
            # node and all related nodes, copy that data over
            # to the complete dict
            for some_node_name in self.__nodes_that_ran_at_least_once:
                self._node_metadata_complete[some_node_name] = \
                    self.__metastacks[some_node_name]._as_dict()

            if blame:
                blame_result = self.__metastacks[node_name]._as_blame()
            elif stack:
                stack_result = self.__metastacks[node_name]

            # reset temporary vars (this isn't strictly necessary, but might
            # free up some memory and avoid confusion)
            self.__reset()

            if blame:
                return blame_result
            elif stack:
                return stack_result
            else:
                return self._node_metadata_complete[node_name]

    def __build_node_metadata(self, initial_node_name):
        self.__reset()
        self.__nodes_that_never_ran.add(initial_node_name)

        iterations = 0
        while not QUIT_EVENT.is_set():  # TODO iteration cap, QUIT_EVENT
            iterations += 1
            if iterations > MAX_METADATA_ITERATIONS:
                assert False
                # TODO
                #reactors = ""
                #for node, reactor in sorted(reactors_that_changed_something_in_last_iteration):
                #    reactors += node + " " + reactor + "\n"
                #raise ValueError(_(
                #    "Infinite loop detected between these metadata reactors:\n"
                #) + reactors)

            try:
                node_name = self.__nodes_that_never_ran.pop()
            except KeyError:
                pass
            else:
                self.__nodes_that_ran_at_least_once.add(node_name)
                self.__initial_run_for_node(node_name)
                continue

            # at this point, we have run all relevant nodes at least once

            # if we have any triggered nodes from below, run their reactors
            # with deps to see if they become unstable

            try:
                node_name = self.__triggered_nodes.pop()
            except KeyError:
                pass
            else:
                self.__run_reactors(self.get_node(node_name), with_deps=True, without_deps=False)
                continue

            # now (re)stabilize all nodes

            encountered_unstable_node = False
            for node, stable in self.__node_stable.items():
                if stable:
                    continue
                self.__run_reactors(node, with_deps=False, without_deps=True)
                if not self.__node_stable[node]:
                    encountered_unstable_node = True
            if encountered_unstable_node:
                # start over until everything is stable
                continue

            # at this point, all nodes should be stable except for their reactors with deps

            encountered_unstable_node = False
            for node in randomize_order(self.__node_stable.keys()):
                self.__run_reactors(node, with_deps=True, without_deps=False)
                if self.__node_stable[node] is False:
                    # something changed on this node, mark all dependent nodes as unstable
                    encountered_unstable_node = True
                    for required_node_name in self.__node_deps.get(node.name, set()):
                        self.__triggered_nodes.add(required_node_name)
            if encountered_unstable_node:
                # start over until everything is stable
                continue

            # if we get here, we're done!
            break

        if self.__keyerrors:
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

    def __initial_run_for_node(self, node_name):
        node = self.get_node(node_name)
        self.__metastacks[node_name] = Metastack()

        with io.job(_("{node}  adding metadata defaults").format(node=bold(node.name))):
            # randomize order to increase chance of exposing clashing defaults
            for defaults_name, defaults in randomize_order(node.metadata_defaults):
                self.__metastacks[node_name]._set_layer(
                    2,
                    defaults_name,
                    defaults,
                )
        self.__metastacks[node_name]._cache_partition(2)

        with io.job(_("{node}  adding group metadata").format(node=bold(node.name))):
            group_order = _flatten_group_hierarchy(node.groups)
            for group_name in group_order:
                self.__metastacks[node_name]._set_layer(
                    0,
                    "group:{}".format(group_name),
                    self.get_group(group_name)._attributes.get('metadata', {}),
                )

        with io.job(_("{node}  adding node metadata").format(node=bold(node.name))):
            self.__metastacks[node_name]._set_layer(
                0,
                "node:{}".format(node_name),
                node._attributes.get('metadata', {}),
            )
        self.__metastacks[node_name]._cache_partition(0)

        self.__reactors_with_deps[node_name] = set()
        # run all reactors once to get started
        self.__run_reactors(node, with_deps=True, without_deps=True)

    def __run_reactors(self, node, with_deps=True, without_deps=True):
        any_reactor_changed = False

        for depsonly in (True, False):
            if depsonly and not with_deps:
                # skip reactors with deps
                continue
            if not depsonly and not without_deps:
                # skip reactors without deps
                continue
            # TODO ideally, we should run the least-run reactors first
            for reactor_name, reactor in randomize_order(node.metadata_reactors):
                if (
                    (depsonly and reactor_name not in self.__reactors_with_deps) or
                    (not depsonly and reactor_name in self.__reactors_with_deps)
                ):
                    # this if makes sure we run reactors with deps first
                    continue
                reactor_changed, deps = self.__run_reactor(node.name, reactor_name, reactor)
                if reactor_changed:
                    any_reactor_changed = True
                if deps:
                    # record that this reactor has dependencies
                    self.__reactors_with_deps[node.name].add(reactor_name)
                    # we could also remove this marker if we end up without
                    # deps again in future iterations, but that is too
                    # unlikely and the housekeeping cost too great
                for required_node_name in deps:
                    if required_node_name not in self.__nodes_that_ran_at_least_once:
                        # we found a node that we didn't need until now
                        self.__nodes_that_never_ran.add(required_node_name)
                    # this is so we know the current node needs to be run
                    # again if the required node changes
                    self.__node_deps.setdefault(required_node_name, set())
                    self.__node_deps[required_node_name].add(node.name)

        self.__node_stable[node] = not any_reactor_changed

    def __run_reactor(self, node_name, reactor_name, reactor):
        if (node_name, reactor_name) in self.__do_not_run_again:
            return False, set()
        self.__partial_metadata_accessed_for = set()
        self.__reactors_run += 1
        try:
            new_metadata = reactor(self.__metastacks[node_name])
        except KeyError as exc:
            self.__keyerrors[(node_name, reactor_name)] = exc
            return False, self.__partial_metadata_accessed_for
        except DoNotRunAgain:
            self.__do_not_run_again.add((node_name, reactor_name))
            # clear any previously stored exception
            try:
                del self.__keyerrors[(node_name, reactor_name)]
            except KeyError:
                pass
            return False, set()
        except Exception as exc:
            io.stderr(_(
                "{x} Exception while executing metadata reactor "
                "{metaproc} for node {node}:"
            ).format(
                x=red("!!!"),
                metaproc=reactor_name,
                node=node_name,
            ))
            raise exc
        else:
            # reactor terminated normally, clear any previously stored exception
            try:
                del self.__keyerrors[(node_name, reactor_name)]
            except KeyError:
                pass

            try:
                this_changed = self.__metastacks[node_name]._set_layer(
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
                    node=node_name,
                ))
                raise exc
            return this_changed, self.__partial_metadata_accessed_for
