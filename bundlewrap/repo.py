from contextlib import suppress
from importlib.machinery import SourceFileLoader
from inspect import isabstract
from os import listdir, mkdir, walk
from os.path import abspath, dirname, isdir, isfile, join
from threading import Lock

from pkg_resources import DistributionNotFound, require, VersionConflict
from tomlkit import parse as parse_toml

from . import items, VERSION_STRING
from .bundle import FILENAME_ITEMS
from .exceptions import (
    NoSuchGroup,
    NoSuchNode,
    NoSuchRepository,
    MissingRepoDependency,
    RepositoryError,
)
from .group import Group
from .metagen import MetadataGenerator
from .node import Node
from .secrets import FILENAME_SECRETS, generate_initial_secrets_cfg, SecretProxy
from .utils import (
    cached_property,
    error_context,
    get_file_contents,
    names,
)
from .utils.scm import get_git_branch, get_git_clean, get_rev
from .utils.dicts import hash_statedict
from .utils.text import mark_for_translation as _, red, validate_name
from .utils.ui import io

DIRNAME_BUNDLES = "bundles"
DIRNAME_DATA = "data"
DIRNAME_HOOKS = "hooks"
DIRNAME_ITEM_TYPES = "items"
DIRNAME_LIBS = "libs"
FILENAME_GROUPS = "groups.py"
FILENAME_NODES = "nodes.py"
FILENAME_REQUIREMENTS = "requirements.txt"

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


class HooksProxy(object):
    def __init__(self, repo, path):
        self.repo = repo
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
            for name, obj in self.repo.get_all_attrs_from_file(filepath).items():
                if name not in HOOK_EVENTS:
                    continue
                self.__module_cache[filename][name] = obj
                self.__registered_hooks[filename].append(name)


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
                m = SourceFileLoader(
                    'bundlewrap.repo.libs_{}'.format(attrname),
                    filepath,
                ).load_module()
            except:
                io.stderr(_("Exception while trying to load {}:").format(filepath))
                raise
            self.__module_cache[attrname] = m
        return self.__module_cache[attrname]


class Repository(MetadataGenerator):
    def __init__(self, repo_path=None):
        if repo_path is None:
            self.path = "/dev/null"
        else:
            self.path = self._discover_root_path(abspath(repo_path))

        self._set_path(self.path)

        self.bundle_names = []
        self.group_dict = {}
        self.node_dict = {}
        self._get_all_attr_code_cache = {}
        self._get_all_attr_result_cache = {}

        # required by MetadataGenerator
        self._node_metadata_proxies = {}
        self._node_metadata_lock = Lock()

        if repo_path is not None:
            self.populate_from_path(self.path)
        else:
            self.item_classes = list(self.items_from_dir(items.__path__[0]))

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
        if group.name in names(self.nodes):
            raise RepositoryError(_("you cannot have a node and a group "
                                    "both named '{}'").format(group.name))
        if group.name in names(self.groups):
            raise RepositoryError(_("you cannot have two groups "
                                    "both named '{}'").format(group.name))
        group.repo = self
        self.group_dict[group.name] = group

    def add_node(self, node):
        """
        Adds the given node object to this repo.
        """
        if node.name in names(self.groups):
            raise RepositoryError(_("you cannot have a node and a group "
                                    "both named '{}'").format(node.name))
        if node.name in names(self.nodes):
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

        open(join(bundle_dir, FILENAME_ITEMS), 'a').close()

    def get_all_attrs_from_file(self, path, base_env=None):
        """
        Reads all 'attributes' (if it were a module) from a source file.
        """
        if base_env is None:
            base_env = {}

        if not base_env and path in self._get_all_attr_result_cache:
            # do not allow caching when passing in a base env because that
            # breaks repeated calls with different base envs for the same
            # file
            return self._get_all_attr_result_cache[path]

        if path not in self._get_all_attr_code_cache:
            source = get_file_contents(path)
            with error_context(path=path):
                self._get_all_attr_code_cache[path] = \
                    compile(source, path, mode='exec')

        code = self._get_all_attr_code_cache[path]
        env = base_env.copy()
        with error_context(path=path):
            exec(code, env)

        if not base_env:
            self._get_all_attr_result_cache[path] = env

        return env

    def nodes_or_groups_from_file(self, path, attribute, preexisting):
        try:
            flat_dict = self.get_all_attrs_from_file(
                path,
                base_env={
                    attribute: preexisting,
                    'libs': self.libs,
                    'repo_path': self.path,
                    'vault': self.vault,
                },
            )[attribute]
        except KeyError:
            raise RepositoryError(_(
                "{} must define a '{}' variable"
            ).format(path, attribute))
        if not isinstance(flat_dict, dict):
            raise ValueError(_("'{v}' in '{p}' must be a dict").format(
                v=attribute,
                p=path,
            ))
        for name, infodict in flat_dict.items():
            infodict.setdefault('file_path', path)
            yield (name, infodict)

    def nodes_or_groups_from_dir(self, directory):
        path = join(self.path, directory)
        if not isdir(path):
            return
        for root_dir, _dirs, files in walk(path):
            for filename in files:
                filepath = join(root_dir, filename)
                if not filename.endswith(".toml") or \
                        not isfile(filepath) or \
                        filename.startswith("_"):
                    continue
                infodict = dict(parse_toml(get_file_contents(filepath)))
                infodict['file_path'] = filepath
                yield filename[:-5], infodict

    def items_from_dir(self, path):
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
                for name, obj in self.get_all_attrs_from_file(filepath).items():
                    if obj == items.Item or name.startswith("_"):
                        continue
                    with suppress(TypeError):
                        if issubclass(obj, items.Item) and not isabstract(obj):
                            yield obj

    def _discover_root_path(self, path):
        while True:
            if self.is_repo(path):
                return path

            previous_component = dirname(path)
            if path == previous_component:
                raise NoSuchRepository

            path = previous_component

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
        toml_groups = dict(self.nodes_or_groups_from_dir("groups"))
        self.group_dict = {}
        for group in self.nodes_or_groups_from_file(self.groups_file, 'groups', toml_groups):
            self.add_group(Group(*group))

        # populate items
        self.item_classes = list(self.items_from_dir(items.__path__[0]))
        for item_class in self.items_from_dir(self.items_dir):
            self.item_classes.append(item_class)

        # populate nodes
        toml_nodes = dict(self.nodes_or_groups_from_dir("nodes"))
        self.node_dict = {}
        for node in self.nodes_or_groups_from_file(self.nodes_file, 'nodes', toml_nodes):
            self.add_node(Node(*node))

    @cached_property
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

        self.hooks = HooksProxy(self, self.hooks_dir)
        self.libs = LibsProxy(self.libs_dir)
