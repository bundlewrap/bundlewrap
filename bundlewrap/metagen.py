from collections import defaultdict, Counter
from contextlib import suppress
from os import environ
from traceback import TracebackException

from .exceptions import MetadataPersistentKeyError
from .metadata import DoNotRunAgain
from .node import _flatten_group_hierarchy
from .utils import randomize_order
from .utils.ui import io, QUIT_EVENT
from .utils.metastack import Metastack
from .utils.text import bold, mark_for_translation as _, red


MAX_METADATA_ITERATIONS = int(environ.get("BW_MAX_METADATA_ITERATIONS", "1000"))


class _StartOver(Exception):
    """
    Raised when metadata processing needs to start from the top.
    """
    pass


class MetadataGenerator:
    # are we currently executing a reactor?
    __in_a_reactor = False

    def __reset(self):
        # reactors that raise DoNotRunAgain
        self.__do_not_run_again = set()
        # reactors that raised KeyErrors (and which ones)
        self.__keyerrors = {}
        # a Metastack for every node
        self.__metastacks = defaultdict(Metastack)
        # mapping each node to all nodes that depend on it
        self.__node_deps = defaultdict(set)
        # how often __run_reactors was called for a node
        self.__node_iterations = defaultdict(int)
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
        # how often we called reactors
        self.__reactors_run = 0
        # how often each reactor changed
        self.__reactor_changes = defaultdict(int)
        # tracks which reactors on a node have look at other nodes
        # through partial_metadata
        self.__reactors_with_deps = defaultdict(set)

    def _metadata_for_node(self, node_name, blame=False, stack=False):
        """
        Returns full or partial metadata for this node. This is the
        primary entrypoint accessed from node.metadata.

        Partial metadata may only be requested from inside a metadata
        reactor.

        If necessary, this method will build complete metadata for this
        node and all related nodes. Related meaning nodes that this node
        depends on in one of its metadata reactors.
        """
        if self.__in_a_reactor:
            if node_name in self._node_metadata_complete:
                io.debug(f"is already complete: {node_name}")
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
                return self.__metastacks[node_name]

        if blame or stack:
            # cannot return cached result here, force rebuild
            with suppress(KeyError):
                del self._node_metadata_complete[node_name]

        with suppress(KeyError):
            return self._node_metadata_complete[node_name]

        # Different worker threads might request metadata at the same time.

        with self._node_metadata_lock:
            with suppress(KeyError):
                # maybe our metadata got completed while waiting for the lock
                return self._node_metadata_complete[node_name]

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

    def __run_new_nodes(self):
        try:
            node_name = self.__nodes_that_never_ran.pop()
        except KeyError:
            pass
        else:
            self.__nodes_that_ran_at_least_once.add(node_name)
            self.__initial_run_for_node(node_name)
            raise _StartOver

    def __run_triggered_nodes(self):
        try:
            node_name = self.__triggered_nodes.pop()
        except KeyError:
            pass
        else:
            io.debug(f"triggered metadata run for {node_name}")
            self.__run_reactors(
                self.get_node(node_name),
                with_deps=True,
                without_deps=False,
            )
            raise _StartOver

    def __run_unstable_nodes(self):
        encountered_unstable_node = False
        for node, stable in self.__node_stable.items():
            if stable:
                continue

            io.debug(f"begin metadata stabilization test for {node.name}")
            self.__run_reactors(node, with_deps=False, without_deps=True)
            if self.__node_stable[node]:
                io.debug(f"metadata stabilized for {node.name}")
            else:
                io.debug(f"metadata remains unstable for {node.name}")
                encountered_unstable_node = True
            if self.__nodes_that_never_ran:
                # we have found a new dependency, process it immediately
                # going wide early should be more efficient
                raise _StartOver
        if encountered_unstable_node:
            # start over until everything is stable
            io.debug("found an unstable node (without_deps=True)")
            raise _StartOver

    def __run_nodes_with_deps(self):
        encountered_unstable_node = False
        for node in randomize_order(self.__node_stable.keys()):
            io.debug(f"begin final stabilization test for {node.name}")
            self.__run_reactors(node, with_deps=True, without_deps=False)
            if not self.__node_stable[node]:
                io.debug(f"{node.name} still unstable")
                encountered_unstable_node = True
            if self.__nodes_that_never_ran:
                # we have found a new dependency, process it immediately
                # going wide early should be more efficient
                raise _StartOver
        if encountered_unstable_node:
            # start over until everything is stable
            io.debug("found an unstable node (with_deps=True)")
            raise _StartOver

    def __build_node_metadata(self, initial_node_name):
        self.__reset()
        self.__nodes_that_never_ran.add(initial_node_name)

        while not QUIT_EVENT.is_set():
            jobmsg = _("{b} ({n} nodes, {r} reactors, {e} runs)").format(
                b=bold(_("running metadata reactors")),
                n=len(self.__nodes_that_never_ran) + len(self.__nodes_that_ran_at_least_once),
                r=len(self.__reactor_changes),
                e=self.__reactors_run,
            )
            try:
                with io.job(jobmsg):
                    # Control flow here is a bit iffy. The functions in this block often raise
                    # _StartOver in order to aggressively process new nodes first etc.
                    # Each method represents a distinct stage of metadata processing that checks
                    # for nodes in certain states as described below.

                    # This checks for newly discovered nodes that haven't seen any processing at
                    # all so far. It is important that we run them as early as possible, so their
                    # static metadata becomes available to other nodes and we recursively discover
                    # additional nodes as quickly as possible.
                    self.__run_new_nodes()
                    # At this point, we have run all relevant nodes at least once.

                    # Nodes become "triggered" when they previously looked something up from a
                    # different node and that second node changed. In this method, we try to figure
                    # out if the change on the node we depend on actually has any effect on the
                    # depending node.
                    self.__run_triggered_nodes()

                    # In this stage, we run all unstable nodes to the point where everything is
                    # stable again, except for those reactors that depend on other nodes.
                    self.__run_unstable_nodes()

                    # The final step is to make sure nothing changes when we run reactors with
                    # dependencies on other nodes. If anything changes, we need to start over so
                    # local-only reactors on a node can react to changes caused by reactors looking
                    # at other nodes.
                    self.__run_nodes_with_deps()

                    # if we get here, we're done!
                    break

            except _StartOver:
                continue

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

        io.debug("metadata generation for selected nodes finished")

    def __initial_run_for_node(self, node_name):
        io.debug(f"initial metadata run for {node_name}")
        node = self.get_node(node_name)
        self.__metastacks[node_name] = Metastack()

        # randomize order to increase chance of exposing clashing defaults
        for defaults_name, defaults in randomize_order(node.metadata_defaults):
            self.__metastacks[node_name]._set_layer(
                2,
                defaults_name,
                defaults,
            )
        self.__metastacks[node_name]._cache_partition(2)

        group_order = _flatten_group_hierarchy(node.groups)
        for group_name in group_order:
            self.__metastacks[node_name]._set_layer(
                0,
                "group:{}".format(group_name),
                self.get_group(group_name)._attributes.get('metadata', {}),
            )

        self.__metastacks[node_name]._set_layer(
            0,
            "node:{}".format(node_name),
            node._attributes.get('metadata', {}),
        )
        self.__metastacks[node_name]._cache_partition(0)

        # run all reactors once to get started
        self.__run_reactors(node, with_deps=True, without_deps=True)

    def __check_iteration_count(self, node_name):
        self.__node_iterations[node_name] += 1
        if self.__node_iterations[node_name] > MAX_METADATA_ITERATIONS:
            top_changers = Counter(self.__reactor_changes).most_common(25)
            msg = _(
                "MAX_METADATA_ITERATIONS({m}) exceeded for {node}, "
                "likely an infinite loop between flip-flopping metadata reactors.\n"
                "These are the reactors that changed most often:\n\n"
            ).format(m=MAX_METADATA_ITERATIONS, node=node_name)
            for reactor, count in top_changers:
                msg += f"  {count}\t{reactor[0]}\t{reactor[1]}\n"
            raise RuntimeError(msg)

    def __run_reactors(self, node, with_deps=True, without_deps=True):
        self.__check_iteration_count(node.name)
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
                    (depsonly and reactor_name not in self.__reactors_with_deps[node.name]) or
                    (not depsonly and reactor_name in self.__reactors_with_deps[node.name])
                ):
                    # this if makes sure we run reactors with deps first
                    continue
                reactor_changed, deps = self.__run_reactor(node.name, reactor_name, reactor)
                io.debug(f"{node.name}:{reactor_name} changed={reactor_changed} deps={deps}")
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
                    self.__node_deps[required_node_name].add(node.name)

        if any_reactor_changed:
            # something changed on this node, mark all dependent nodes as unstable
            for required_node_name in self.__node_deps[node.name]:
                io.debug(f"{node.name} triggering metadata rerun on {required_node_name}")
                self.__triggered_nodes.add(required_node_name)

        if with_deps and any_reactor_changed:
            self.__node_stable[node] = False
        elif without_deps:
            self.__node_stable[node] = not any_reactor_changed

    def __run_reactor(self, node_name, reactor_name, reactor):
        if (node_name, reactor_name) in self.__do_not_run_again:
            return False, set()
        self.__partial_metadata_accessed_for = set()
        self.__reactors_run += 1
        # make sure the reactor doesn't react to its own output
        old_metadata = self.__metastacks[node_name]._pop_layer(1, reactor_name)
        self.__in_a_reactor = True
        try:
            new_metadata = reactor(self.__metastacks[node_name])
        except KeyError as exc:
            self.__keyerrors[(node_name, reactor_name)] = exc
            return False, self.__partial_metadata_accessed_for
        except DoNotRunAgain:
            self.__do_not_run_again.add((node_name, reactor_name))
            # clear any previously stored exception
            with suppress(KeyError):
                del self.__keyerrors[(node_name, reactor_name)]
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
        finally:
            self.__in_a_reactor = False

        # reactor terminated normally, clear any previously stored exception
        with suppress(KeyError):
            del self.__keyerrors[(node_name, reactor_name)]

        try:
            self.__metastacks[node_name]._set_layer(
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

        changed = old_metadata != new_metadata
        if changed:
            self.__reactor_changes[(node_name, reactor_name)] += 1

        return changed, self.__partial_metadata_accessed_for
