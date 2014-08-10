from imp import load_source
from os import listdir, mkdir
from os.path import isdir, isfile, join

from . import items
from .exceptions import NoSuchGroup, NoSuchNode, NoSuchRepository, RepositoryError
from .group import Group
from .node import Node
from . import utils
from .utils.scm import get_rev
from .utils.text import mark_for_translation as _, validate_name

DIRNAME_BUNDLES = "bundles"
DIRNAME_DATA = "data"
DIRNAME_HOOKS = "hooks"
DIRNAME_ITEM_TYPES = "items"
DIRNAME_LIBS = "libs"
FILENAME_GROUPS = "groups.py"
FILENAME_NODES = "nodes.py"

HOOK_EVENTS = (
    'action_run_start',
    'action_run_end',
    'apply_start',
    'apply_end',
    'item_apply_start',
    'item_apply_end',
    'node_apply_start',
    'node_apply_end',
    'node_run_start',
    'node_run_end',
    'run_start',
    'run_end',
)

INITIAL_CONTENT = {
    FILENAME_GROUPS: _("""
groups = {
    #'group1': {
    #    'bundles': (
    #        'bundle1',
    #    ),
    #    'members': (
    #        'node1',
    #    ),
    #    'subgroups': (
    #        'group2',
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
    'node1': {
        'hostname': "localhost",
    },
}
    """),
}


def groups_from_file(filepath, libs):
    """
    Returns all groups as defined in the given groups.py.
    """
    try:
        flat_group_dict = utils.getattr_from_file(
            filepath,
            'groups',
            base_env={'libs': libs},
        )
    except KeyError:
        raise RepositoryError(_(
            "{} must define a 'groups' variable"
        ).format(filepath))
    for groupname, infodict in flat_group_dict.items():
        yield Group(groupname, infodict)


class HooksProxy(object):
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

            # check the cache for the imported function,
            # import if necessary
            for filename in files:
                if filename not in self.__module_cache:
                    self.__module_cache[filename] = {}
                    filepath = join(self.__path, filename)
                    for name, obj in utils.get_all_attrs_from_file(filepath).items():
                        if name not in HOOK_EVENTS:
                            continue
                        self.__module_cache[filename][name] = obj

            # define a function that calls all hook functions
            def hook(*args, **kwargs):
                for filename in files:
                    self.__module_cache[filename][event](*args, **kwargs)
            self.__hook_cache[event] = hook

        return self.__hook_cache[event]

    def __getstate__(self):
        return (self.__path, self.__registered_hooks)

    def __setstate__(self, state):
        self.__hook_cache = {}
        self.__module_cache = {}
        self.__path = state[0]
        self.__registered_hooks = state[1]

    def _register_hooks(self):
        """
        Builds an internal dictionary of defined hooks that is used in
        __getstate__ to avoid reimporting all hook modules in child
        processes.

        We have to do this since we cannot pass the imported functions
        to a child process. The dumb-but-simple approach would be to
        rediscover hooks in every child process (which might be costly).

        From this dictionary the child process knows which hooks exist
        and can import them only as needed.

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


def items_from_path(itempath):
    """
    Looks for Item subclasses in the items directory that ships with
    bundlewrap and the local items dir of this specific repo.

    An alternative method would involve metaclasses (as Django
    does it), but then it gets very hard to have two separate repos
    in the same process, because both of them would register config
    item classes globally.
    """
    for path in items.__path__ + [itempath]:
        if not isdir(path):
            continue
        for filename in listdir(path):
            filepath = join(path, filename)
            if not filename.endswith(".py") or \
                    not isfile(filepath) or \
                    filename.startswith("_"):
                continue
            for name, obj in \
                    utils.get_all_attrs_from_file(filepath).items():
                if obj == items.Item or name.startswith("_"):
                    continue
                try:
                    if issubclass(obj, items.Item):
                        yield obj
                except TypeError:
                    pass


class LibsProxy(object):
    def __init__(self, path):
        self.__module_cache = {}
        self.__path = path

    def __getattr__(self, attrname):
        if attrname not in self.__module_cache:
            filename = attrname + ".py"
            filepath = join(self.__path, filename)
            m = load_source('bundlewrap.repo.libs_{}'.format(attrname), filepath)
            self.__module_cache[attrname] = m
        return self.__module_cache[attrname]

    def __getstate__(self):
        return self.__path

    def __setstate__(self, state):
        self.__module_cache = {}
        self.__path = state


def nodes_from_file(filepath, libs):
    """
    Returns a list of nodes as defined in the given nodes.py.
    """
    try:
        flat_node_dict = utils.getattr_from_file(
            filepath,
            'nodes',
            base_env={'libs': libs},
        )
    except KeyError:
        raise RepositoryError(
            _("{} must define a 'nodes' variable").format(filepath)
        )
    for nodename, infodict in flat_node_dict.items():
        yield Node(nodename, infodict)


class Repository(object):
    def __init__(self, repo_path=None, password=None):
        self.path = "/dev/null" if repo_path is None else repo_path

        self._set_path(self.path)

        self.bundle_names = []
        self.group_dict = {}
        self.item_classes = []
        self.node_dict = {}
        self.password = password

        if repo_path is not None:
            self.populate_from_path(repo_path)

    def __eq__(self, other):
        if self.path == "/dev/null":
            # in-memory repos are never equal
            return False
        return self.path == other.path

    def __getstate__(self):
        """
        Removes cached item classes prior to pickling because they are loaded
        dynamically and can't be pickled.
        """
        self.item_classes = []
        return self.__dict__

    def __setstate__(self, dict):
        self.__dict__ = dict
        for item_class in items_from_path(self.items_dir):
            self.item_classes.append(item_class)

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

    @classmethod
    def create(cls, path):
        """
        Creates and returns a repository at path, which must exist and
        be empty.
        """
        for filename, content in INITIAL_CONTENT.items():
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

        open(join(bundle_dir, "bundle.py"), 'a').close()

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

    @property
    def groups(self):
        return sorted(self.group_dict.values())

    def groups_for_node(self, node):
        for group in self.groups:
            if node in group.nodes:
                yield group

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

    def populate_from_path(self, path):
        if not self.is_repo(path):
            raise NoSuchRepository(
                _("'{}' is not a bundlewrap repository").format(path)
            )

        if path != self.path:
            self._set_path(path)

        # populate bundles
        self.bundle_names = []
        for dir_entry in listdir(self.bundles_dir):
            if validate_name(dir_entry):
                self.bundle_names.append(dir_entry)

        # populate groups
        self.group_dict = {}
        for group in groups_from_file(self.groups_file, self.libs):
            self.add_group(group)

        # populate items
        self.item_classes = []
        for item_class in items_from_path(self.items_dir):
            self.item_classes.append(item_class)

        # populate nodes
        self.node_dict = {}
        for node in nodes_from_file(self.nodes_file, self.libs):
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
