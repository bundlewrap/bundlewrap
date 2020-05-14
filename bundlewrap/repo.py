from imp import load_source
from inspect import isabstract
from os import environ, listdir, mkdir, walk
from os.path import isdir, isfile, join
from threading import Lock

from pkg_resources import DistributionNotFound, require, VersionConflict

from . import items, utils, VERSION_STRING
from .bundle import FILENAME_BUNDLE
from .exceptions import (
    NoSuchGroup,
    NoSuchNode,
    NoSuchRepository,
    MissingRepoDependency,
    RepositoryError,
)
from .group import Group
from .metadata import DoNotRunAgain
from .node import _flatten_group_hierarchy, Node
from .secrets import FILENAME_SECRETS, generate_initial_secrets_cfg, SecretProxy
from .utils import cached_property, names, randomize_order
from .utils.scm import get_git_branch, get_git_clean, get_rev
from .utils.dicts import hash_statedict
from .utils.metastack import Metastack
from .utils.text import bold, mark_for_translation as _, red, validate_name
from .utils.ui import io, QUIT_EVENT

DIRNAME_BUNDLES = "bundles"
DIRNAME_DATA = "data"
DIRNAME_HOOKS = "hooks"
DIRNAME_ITEM_TYPES = "items"
DIRNAME_LIBS = "libs"
FILENAME_GROUPS = "groups.py"
FILENAME_NODES = "nodes.py"
FILENAME_REQUIREMENTS = "requirements.txt"
MAX_METADATA_ITERATIONS = int(environ.get("BW_MAX_METADATA_ITERATIONS", "100"))

HOOK_EVENTS = (
    'action_run_end',
    'action_run_start',
    'apply_end',
    'apply_start',
    'item_apply_end',
    'item_apply_start',
    'lock_add',
    'lock_remove',
    'lock_show',
    'node_apply_end',
    'node_apply_start',
    'node_run_end',
    'node_run_start',
    'run_end',
    'run_start',
    'test',
    'test_node',
)

INITIAL_CONTENT = {
    FILENAME_GROUPS: _("""
groups = {
    #'group-1': {
    #    'bundles': (
    #        'bundle-1',
    #    ),
    #    'members': (
    #        'node-1',
    #    ),
    #    'subgroups': (
    #        'group-2',
    #    ),
    #},
    'all': {
        'member_patterns': (
            r".*",
        ),
    },
}
    """),

    FILENAME_NODES: _("""
nodes = {
    'node-1': {
        'hostname': "localhost",
    },
}
    """),
    FILENAME_REQUIREMENTS: "bundlewrap>={}\n".format(VERSION_STRING),
    FILENAME_SECRETS: generate_initial_secrets_cfg,
}


def groups_from_file(filepath, libs, repo_path, vault):
    """
    Returns all groups as defined in the given groups.py.
    """
    try:
        flat_group_dict = utils.getattr_from_file(
            filepath,
            'groups',
            base_env={
                'libs': libs,
                'repo_path': repo_path,
                'vault': vault,
            },
        )
    except KeyError:
        raise RepositoryError(_(
            "{} must define a 'groups' variable"
        ).format(filepath))
    for groupname, infodict in flat_group_dict.items():
        yield Group(groupname, infodict)


class HooksProxy:
    def __init__(self, path):
        self.__hook_cache = {}
        self.__module_cache = {}
        self.__path = path
        self.__registered_hooks = None

    def __getattr__(self, attrname):
        if attrname not in HOOK_EVENTS:
            raise AttributeError

        if self.__registered_hooks is None:
            self._register_hooks()

        event = attrname

        if event not in self.__hook_cache:
            # build a list of files that define a hook for the event
            files = []
            for filename, events in self.__registered_hooks.items():
                if event in events:
                    files.append(filename)

            # define a function that calls all hook functions
            def hook(*args, **kwargs):
                for filename in files:
                    self.__module_cache[filename][event](*args, **kwargs)
            self.__hook_cache[event] = hook

        return self.__hook_cache[event]

    def _register_hooks(self):
        """
        Builds an internal dictionary of defined hooks.

        Priming __module_cache here is just a performance shortcut and
        could be left out.
        """
        self.__registered_hooks = {}

        if not isdir(self.__path):
            return

        for filename in listdir(self.__path):
            filepath = join(self.__path, filename)
            if not filename.endswith(".py") or \
                    not isfile(filepath) or \
                    filename.startswith("_"):
                continue
            self.__module_cache[filename] = {}
            self.__registered_hooks[filename] = []
            for name, obj in utils.get_all_attrs_from_file(filepath).items():
                if name not in HOOK_EVENTS:
                    continue
                self.__module_cache[filename][name] = obj
                self.__registered_hooks[filename].append(name)


def items_from_path(path):
    """
    Looks for Item subclasses in the given path.

    An alternative method would involve metaclasses (as Django
    does it), but then it gets very hard to have two separate repos
    in the same process, because both of them would register config
    item classes globally.
    """
    if not isdir(path):
        return
    for root_dir, _dirs, files in walk(path):
        for filename in files:
            filepath = join(root_dir, filename)
            if not filename.endswith(".py") or \
                    not isfile(filepath) or \
                    filename.startswith("_"):
                continue
            for name, obj in utils.get_all_attrs_from_file(filepath).items():
                if obj == items.Item or name.startswith("_"):
                    continue
                try:
                    if issubclass(obj, items.Item) and not isabstract(obj):
                        yield obj
                except TypeError:
                    pass


class LibsProxy:
    def __init__(self, path):
        self.__module_cache = {}
        self.__path = path

    def __getattr__(self, attrname):
        if attrname.startswith("__") and attrname.endswith("__"):
            raise AttributeError(attrname)
        if attrname not in self.__module_cache:
            filename = attrname + ".py"
            filepath = join(self.__path, filename)
            try:
                m = load_source('bundlewrap.repo.libs_{}'.format(attrname), filepath)
            except:
                io.stderr(_("Exception while trying to load {}:").format(filepath))
                raise
            self.__module_cache[attrname] = m
        return self.__module_cache[attrname]


def nodes_from_file(filepath, libs, repo_path, vault):
    """
    Returns a list of nodes as defined in the given nodes.py.
    """
    try:
        flat_node_dict = utils.getattr_from_file(
            filepath,
            'nodes',
            base_env={
                'libs': libs,
                'repo_path': repo_path,
                'vault': vault,
            },
        )
    except KeyError:
        raise RepositoryError(
            _("{} must define a 'nodes' variable").format(filepath)
        )
    for nodename, infodict in flat_node_dict.items():
        yield Node(nodename, infodict)


class Repository:
    def __init__(self, repo_path=None):
        self.path = "/dev/null" if repo_path is None else repo_path

        self._set_path(self.path)

        self.bundle_names = []
        self.group_dict = {}
        self.node_dict = {}
        self._node_metadata_complete = {}
        self._node_metadata_lock = Lock()

        if repo_path is not None:
            self.populate_from_path(repo_path)
        else:
            self.item_classes = list(items_from_path(items.__path__[0]))

    def __eq__(self, other):
        if self.path == "/dev/null":
            # in-memory repos are never equal
            return False
        return self.path == other.path

    def __repr__(self):
        return "<Repository at '{}'>".format(self.path)

    @staticmethod
    def is_repo(path):
        """
        Validates whether the given path is a bundlewrap repository.
        """
        try:
            assert isdir(path)
            assert isfile(join(path, "nodes.py"))
            assert isfile(join(path, "groups.py"))
        except AssertionError:
            return False
        return True

    def add_group(self, group):
        """
        Adds the given group object to this repo.
        """
        if group.name in utils.names(self.nodes):
            raise RepositoryError(_("you cannot have a node and a group "
                                    "both named '{}'").format(group.name))
        if group.name in utils.names(self.groups):
            raise RepositoryError(_("you cannot have two groups "
                                    "both named '{}'").format(group.name))
        group.repo = self
        self.group_dict[group.name] = group

    def add_node(self, node):
        """
        Adds the given node object to this repo.
        """
        if node.name in utils.names(self.groups):
            raise RepositoryError(_("you cannot have a node and a group "
                                    "both named '{}'").format(node.name))
        if node.name in utils.names(self.nodes):
            raise RepositoryError(_("you cannot have two nodes "
                                    "both named '{}'").format(node.name))

        node.repo = self
        self.node_dict[node.name] = node

    @cached_property
    def branch(self):
        return get_git_branch()

    @cached_property
    def cdict(self):
        repo_dict = {}
        for node in self.nodes:
            repo_dict[node.name] = node.hash()
        return repo_dict

    @cached_property
    def clean(self):
        return get_git_clean()

    @classmethod
    def create(cls, path):
        """
        Creates and returns a repository at path, which must exist and
        be empty.
        """
        for filename, content in INITIAL_CONTENT.items():
            if callable(content):
                content = content()
            with open(join(path, filename), 'w') as f:
                f.write(content.strip() + "\n")

        mkdir(join(path, DIRNAME_BUNDLES))
        mkdir(join(path, DIRNAME_ITEM_TYPES))

        return cls(path)

    def create_bundle(self, bundle_name):
        """
        Creates an empty bundle.
        """
        if not validate_name(bundle_name):
            raise ValueError(_("'{}' is not a valid bundle name").format(bundle_name))

        bundle_dir = join(self.bundles_dir, bundle_name)

        # deliberately not using makedirs() so this will raise an
        # exception if the directory exists
        mkdir(bundle_dir)
        mkdir(join(bundle_dir, "files"))

        open(join(bundle_dir, FILENAME_BUNDLE), 'a').close()

    def create_node(self, node_name):
        """
        Creates an adhoc node with the given name.
        """
        node = Node(node_name)
        self.add_node(node)
        return node

    def get_group(self, group_name):
        try:
            return self.group_dict[group_name]
        except KeyError:
            raise NoSuchGroup(group_name)

    def get_node(self, node_name):
        try:
            return self.node_dict[node_name]
        except KeyError:
            raise NoSuchNode(node_name)

    def group_membership_hash(self):
        return hash_statedict(sorted(names(self.groups)))

    @property
    def groups(self):
        return sorted(self.group_dict.values())

    def hash(self):
        return hash_statedict(self.cdict)

    @property
    def nodes(self):
        return sorted(self.node_dict.values())

    def nodes_in_all_groups(self, group_names):
        """
        Returns a list of nodes where every node is a member of every
        group given.
        """
        base_group = set(self.get_group(group_names[0]).nodes)
        for group_name in group_names[1:]:
            if not base_group:
                # quit early if we have already eliminated every node
                break
            base_group.intersection_update(set(self.get_group(group_name).nodes))
        result = list(base_group)
        result.sort()
        return result

    def nodes_in_any_group(self, group_names):
        """
        Returns all nodes that are a member of at least one of the given
        groups.
        """
        for node in self.nodes:
            if node.in_any_group(group_names):
                yield node

    def nodes_in_group(self, group_name):
        """
        Returns a list of nodes in the given group.
        """
        return self.nodes_in_all_groups([group_name])

    def _metadata_for_node(self, node_name, partial=False, blame=False):
        """
        Returns full or partial metadata for this node.

        Partial metadata may only be requested from inside a metadata
        reactor.

        If necessary, this method will build complete metadata for this
        node and all related nodes. Related meaning nodes that this node
        depends on in one of its metadata processors.
        """
        if partial:
            if node_name in self._node_metadata_complete:
                # We already completed metadata for this node, but partial must
                # return a Metastack, so we build a single-layered one just for
                # the interface.
                metastack = Metastack()
                metastack._set_layer(
                    "flattened",
                    self._node_metadata_complete[node_name],
                )
                return metastack
            else:
                # Return the WIP Metastack or an empty one if we didn't start
                # yet.
                self._nodes_we_need_metadata_for.add(node_name)
                return self._metastacks.setdefault(node_name, Metastack())

        try:
            return self._node_metadata_complete[node_name]
        except KeyError:
            pass

        # Different worker threads might request metadata at the same time.
        # This creates problems for the following variables:
        #
        #    self._metastacks
        #    self._nodes_we_need_metadata_for
        #
        # Chaos would ensue if we allowed multiple instances of
        # _build_node_metadata() running in parallel, messing with these
        # vars. So we use a lock and reset the vars before and after.

        with self._node_metadata_lock:
            try:
                # maybe our metadata got completed while waiting for the lock
                return self._node_metadata_complete[node_name]
            except KeyError:
                pass

            # set up temporary vars
            self._metastacks = {}
            self._nodes_we_need_metadata_for = {node_name}

            self._build_node_metadata()

            io.debug("completed metadata for {} nodes".format(
                len(self._nodes_we_need_metadata_for),
            ))
            # now that we have completed all metadata for this
            # node and all related nodes, copy that data over
            # to the complete dict
            for node_name in self._nodes_we_need_metadata_for:
                self._node_metadata_complete[node_name] = \
                    self._metastacks[node_name]._as_dict()

            if blame:
                blame_result = self._metastacks[node_name]._blame()

            # reset temporary vars (this isn't strictly necessary, but might
            # free up some memory and avoid confusion)
            self._metastacks = {}
            self._nodes_we_need_metadata_for = set()

            if blame:
                return blame_result
            else:
                return self._node_metadata_complete[node_name]

    def _build_node_metadata(self):
        """
        Builds complete metadata for all nodes that appear in
        self._nodes_we_need_metadata_for.
        """
        # Prevents us from reassembling static metadata needlessly and
        # helps us detect nodes pulled into self._nodes_we_need_metadata_for
        # by node.partial_metadata.
        nodes_with_completed_static_metadata = set()
        # these reactors have indicated that they do not need to be run again
        do_not_run_again = set()
        # these reactors have raised KeyErrors
        keyerrors = {}
        # these reactors have actually produced a non-falsy result
        results_observed_from = set()
        # loop detection
        iterations = 0
        reactors_that_changed_something_in_last_iteration = set()

        while not QUIT_EVENT.is_set():
            iterations += 1
            if iterations > MAX_METADATA_ITERATIONS:
                reactors = ""
                for node, reactor in sorted(reactors_that_changed_something_in_last_iteration):
                    reactors += node + " " + reactor + "\n"
                raise ValueError(_(
                    "Infinite loop detected between these metadata reactors:\n"
                ) + reactors)

            # First, get the static metadata out of the way
            for node_name in list(self._nodes_we_need_metadata_for):
                if QUIT_EVENT.is_set():
                    break
                node = self.get_node(node_name)
                # check if static metadata for this node is already done
                if node_name in nodes_with_completed_static_metadata:
                    continue
                self._metastacks[node_name] = Metastack()

                with io.job(_("{node}  adding metadata defaults").format(node=bold(node.name))):
                    # randomize order to increase chance of exposing clashing defaults
                    for defaults_name, defaults in randomize_order(node.metadata_defaults):
                        self._metastacks[node_name]._set_layer(
                            defaults_name,
                            defaults,
                        )

                with io.job(_("{node}  adding group metadata").format(node=bold(node.name))):
                    group_order = _flatten_group_hierarchy(node.groups)
                    for group_name in group_order:
                        self._metastacks[node_name]._set_layer(
                            "group:{}".format(group_name),
                            self.get_group(group_name).metadata,
                        )

                with io.job(_("{node}  adding node metadata").format(node=bold(node.name))):
                    self._metastacks[node_name]._set_layer(
                        "node:{}".format(node_name),
                        node._node_metadata,
                    )

                # This will ensure node/group metadata and defaults are
                # skipped over in future iterations.
                nodes_with_completed_static_metadata.add(node_name)

            # Now for the interesting part: We run all metadata reactors
            # until none of them return changed metadata anymore.
            any_reactor_returned_changed_metadata = False
            reactors_that_changed_something_in_last_iteration = set()

            # randomize order to increase chance of exposing unintended
            # non-deterministic effects of execution order
            for node_name in randomize_order(self._nodes_we_need_metadata_for):
                if QUIT_EVENT.is_set():
                    break
                node = self.get_node(node_name)

                with io.job(_("{node}  running metadata reactors").format(node=bold(node.name))):
                    for reactor_name, reactor in randomize_order(node.metadata_reactors):
                        if (node_name, reactor_name) in do_not_run_again:
                            continue
                        try:
                            new_metadata = reactor(self._metastacks[node.name])
                        except KeyError as exc:
                            keyerrors[(node_name, reactor_name)] = exc
                        except DoNotRunAgain:
                            do_not_run_again.add((node_name, reactor_name))
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
                        else:
                            # reactor terminated normally, clear any previously stored exception
                            try:
                                del keyerrors[(node_name, reactor_name)]
                            except KeyError:
                                pass
                            if new_metadata:
                                results_observed_from.add((node_name, reactor_name))

                            this_changed = self._metastacks[node_name]._set_layer(
                                reactor_name,
                                new_metadata,
                            )
                            if this_changed:
                                reactors_that_changed_something_in_last_iteration.add(
                                    (node_name, reactor_name),
                                )
                                any_reactor_returned_changed_metadata = True

            if not any_reactor_returned_changed_metadata:
                if nodes_with_completed_static_metadata != self._nodes_we_need_metadata_for:
                    # During metadata reactor execution, partial metadata may
                    # have been requested for nodes we did not previously
                    # consider. We still need to make sure to generate static
                    # metadata for these new nodes, as that may trigger
                    # additional results from metadata reactors.
                    continue
                else:
                    break

        if keyerrors:
            reactors = ""
            for source, exc in keyerrors.items():
                node_name, reactor = source
                reactors += "{}  {}  {}\n".format(node_name, reactor, exc)
            raise ValueError(_(
                "These metadata reactors raised a KeyError "
                "even after all other reactors were done:\n"
            ) + reactors)

    def metadata_hash(self):
        repo_dict = {}
        for node in self.nodes:
            repo_dict[node.name] = node.metadata_hash()
        return hash_statedict(repo_dict)

    def populate_from_path(self, path):
        if not self.is_repo(path):
            raise NoSuchRepository(
                _("'{}' is not a bundlewrap repository").format(path)
            )

        if path != self.path:
            self._set_path(path)

        # check requirements.txt
        try:
            with open(join(path, FILENAME_REQUIREMENTS)) as f:
                lines = f.readlines()
        except:
            pass
        else:
            try:
                require(lines)
            except DistributionNotFound as exc:
                raise MissingRepoDependency(_(
                    "{x} Python package '{pkg}' is listed in {filename}, but wasn't found. "
                    "You probably have to install it with `pip install {pkg}`."
                ).format(
                    filename=FILENAME_REQUIREMENTS,
                    pkg=exc.req,
                    x=red("!"),
                ))
            except VersionConflict as exc:
                raise MissingRepoDependency(_(
                    "{x} Python package '{required}' is listed in {filename}, "
                    "but only '{existing}' was found. "
                    "You probably have to upgrade it with `pip install {required}`."
                ).format(
                    existing=exc.dist,
                    filename=FILENAME_REQUIREMENTS,
                    required=exc.req,
                    x=red("!"),
                ))

        self.vault = SecretProxy(self)

        # populate bundles
        self.bundle_names = []
        for dir_entry in listdir(self.bundles_dir):
            if validate_name(dir_entry):
                self.bundle_names.append(dir_entry)

        # populate groups
        self.group_dict = {}
        for group in groups_from_file(self.groups_file, self.libs, self.path, self.vault):
            self.add_group(group)

        # populate items
        self.item_classes = list(items_from_path(items.__path__[0]))
        for item_class in items_from_path(self.items_dir):
            self.item_classes.append(item_class)

        # populate nodes
        self.node_dict = {}
        for node in nodes_from_file(self.nodes_file, self.libs, self.path, self.vault):
            self.add_node(node)

    @utils.cached_property
    def revision(self):
        return get_rev()

    def _set_path(self, path):
        self.path = path
        self.bundles_dir = join(self.path, DIRNAME_BUNDLES)
        self.data_dir = join(self.path, DIRNAME_DATA)
        self.hooks_dir = join(self.path, DIRNAME_HOOKS)
        self.items_dir = join(self.path, DIRNAME_ITEM_TYPES)
        self.groups_file = join(self.path, FILENAME_GROUPS)
        self.libs_dir = join(self.path, DIRNAME_LIBS)
        self.nodes_file = join(self.path, FILENAME_NODES)

        self.hooks = HooksProxy(self.hooks_dir)
        self.libs = LibsProxy(self.libs_dir)
