from contextlib import suppress
from importlib.util import module_from_spec, spec_from_file_location
from inspect import isabstract
from os import listdir, mkdir, walk
from os.path import abspath, dirname, isdir, isfile, join
from sys import version_info


try:
    from tomllib import loads as toml_load
except ImportError:
    from rtoml import load as toml_load

VERSION_NEW_PACKAGING = (3, 10)
if version_info >= VERSION_NEW_PACKAGING:
    from importlib import metadata
    from packaging.requirements import Requirement
else:
    from pkg_resources import DistributionNotFound, require, VersionConflict  # needs setuptools

from . import items, VERSION_STRING
from .bundle import FILENAME_ITEMS
from .exceptions import (
    NoSuchGroup,
    NoSuchNode,
    NoSuchTarget,
    NoSuchRepository,
    MissingRepoDependency,
    RepositoryError,
)
from .group import Group
from .metagen import MetadataGenerator
from .node import Node, NODE_ATTRS
from .secrets import FILENAME_SECRETS, generate_initial_secrets_cfg, SecretProxy
from .utils import (
    cached_property,
    error_context,
    get_file_contents,
    names,
)
from .utils.dicts import hash_statedict
from .utils.scm import get_git_branch, get_git_clean, get_rev
from .utils.node_lambda import parallel_node_eval
from .utils.text import bold, mark_for_translation as _, red, validate_name
from .utils.ui import io

DIRNAME_BUNDLES = "bundles"
DIRNAME_DATA = "data"
DIRNAME_HOOKS = "hooks"
DIRNAME_ITEM_TYPES = "items"
DIRNAME_LIBS = "libs"
FILENAME_GROUPS = "groups.py"
FILENAME_MAGIC_STRINGS = "magic_strings.py"
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
    'node_ssh_connect',
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
#groups['group-1'] = {
#    'bundles': (
#        'bundle-1',
#    ),
#    'members': (
#        'node-1',
#    ),
#    'subgroups': (
#        'group-2',
#    ),
#}

groups['all'] = {
    'member_patterns': (
        r".*",
    ),
}
    """),

    FILENAME_NODES: _("""
nodes['node-1'] = {
    'hostname': "localhost",
}
    """),
    FILENAME_REQUIREMENTS: "bundlewrap>={}\n".format(VERSION_STRING),
    FILENAME_SECRETS: generate_initial_secrets_cfg,
}


def _check_requirements(lines):
    reqs = [Requirement(line) for line in lines]

    for req in reqs:
        # Ignore packages with a marker that does *not* apply to
        # the current system.
        if req.marker is not None and not req.marker.evaluate():
            continue

        for installed in metadata.distributions():
            if req.name.lower() == installed.name.lower():
                if req.specifier.contains(installed.version):
                    # We're good.
                    break
                else:
                    raise MissingRepoDependency(_(
                        "{x} Python package '{required}' is listed in {filename}, "
                        "but only '{existing_name}=={existing_version}' was found. "
                        "You probably have to upgrade it with `pip install {required}`."
                    ).format(
                        existing_name=installed.name,
                        existing_version=installed.version,
                        filename=FILENAME_REQUIREMENTS,
                        required=req,
                        x=red("!"),
                    ))
        else:
            raise MissingRepoDependency(_(
                "{x} Python package '{pkg}' is listed in {filename}, but wasn't found. "
                "You probably have to install it with `pip install {pkg}`."
            ).format(
                filename=FILENAME_REQUIREMENTS,
                pkg=req,
                x=red("!"),
            ))


# TODO Remove when dropping support for Python 3.9
def _check_requirements_legacy(lines):
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


class HooksProxy:
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
            def hook(**kwargs):
                level_hint = _("repo-level hooks")
                if 'node' in kwargs:
                    level_hint = _("node-level hooks for node {}").format(kwargs['node'].name)
                elif 'nodes' in kwargs:
                    level_hint += _(" for {} nodes").format(len(kwargs['nodes']))

                for filename in files:
                    with io.job(_("{event}  Running {level_hint} from {filename}").format(
                        event=bold(event),
                        level_hint=level_hint,
                        filename=filename,
                    )):
                        with error_context(filename=filename):
                            self.__module_cache[filename][event](**kwargs)
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
                spec = spec_from_file_location(
                    'bundlewrap.repo.libs_{}'.format(attrname),
                    filepath,
                )
                mod = module_from_spec(spec)
                spec.loader.exec_module(mod)
            except Exception:
                io.stderr(_("Exception while trying to load {}:").format(filepath))
                raise
            self.__module_cache[attrname] = mod
        return self.__module_cache[attrname]


class Repository(MetadataGenerator):
    def __init__(self, repo_path=None):
        super().__init__()

        if repo_path is None:
            self.path = "/dev/null"
        else:
            self.path = self._discover_root_path(abspath(repo_path))

        self._set_path(self.path)

        self.bundle_names = []
        self.group_dict = {}
        self.node_dict = {}
        self.node_attribute_functions = {}
        self.magic_string_functions = {}
        self._get_all_attr_code_cache = {}
        self._get_all_attr_result_cache = {}

        with io.job("Loading repository"):
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
            assert isdir(join(path, DIRNAME_BUNDLES))
            assert isfile(join(path, FILENAME_NODES))
            assert isfile(join(path, FILENAME_GROUPS))
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
        if listdir(path):
            raise ValueError(_("'{}' is not an empty directory".format(
                path
            )))

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
        def node_attribute(func):
            if func.__name__ in NODE_ATTRS:
                raise RepositoryError(_(
                    "cannot redefine builtin attribute '{attr}' as @node_attribute in nodes.py"
                ).format(attr=func.__name__))
            self.node_attribute_functions[func.__name__] = func
            return func

        try:
            flat_dict = self.get_all_attrs_from_file(
                path,
                base_env={
                    attribute: preexisting,
                    'libs': self.libs,
                    'node_attribute': node_attribute,
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
            return {}
        result = {}
        for root_dir, _dirs, files in walk(path):
            for filename in files:
                filepath = join(root_dir, filename)
                if not filename.endswith(".toml") or \
                        not isfile(filepath) or \
                        filename.startswith("_"):
                    continue
                entity_name = filename[:-5]
                if entity_name in result:
                    raise RepositoryError(_(
                        "Duplicate definition of {entity_name} in {file1} and {file2}"
                    ).format(
                        entity_name=entity_name,
                        file1=filepath,
                        file2=result[entity_name]['file_path'],
                    ))
                with error_context(filepath=filepath):
                    infodict = toml_load(get_file_contents(filepath).decode())
                infodict['file_path'] = filepath
                result[entity_name] = infodict
        return result

    def get_magic_strings(self):
        if not isfile(self.magic_strings_file):
            return

        def magic_string(func):
            self.magic_string_functions[func.__name__] = func
            return func

        # We do not store the gotten attrs anywhere, because we're
        # only interested in the defined magic strings.
        self.get_all_attrs_from_file(
            self.magic_strings_file,
            base_env={
                'libs': self.libs,
                'magic_string': magic_string,
                'repo_path': self.path,
                'vault': self.vault,
            },
        )

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
        # TODO 5.0 make this a cached set
        return sorted(self.group_dict.values())

    def hash(self):
        return hash_statedict(self.cdict)

    @property
    def nodes(self):
        # TODO 5.0 make this a cached set
        return sorted(self.node_dict.values())

    def nodes_in_all_groups(self, group_names):
        """
        Returns a list of nodes where every node is a member of every
        group given.

        :param group_names: list of names of the groups to check for
        :return list of nodes where every node is a member of every group given.
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

        :param group_names: list of names of the groups to check for
        :return list of nodes which are in at least one of given groups
        """
        for node in self.nodes:
            if node.in_any_group(group_names):
                yield node

    def nodes_in_group(self, group_name):
        """
        Returns a list of nodes in the given group.

        :param group_name: name of the group to check for
        :return list of nodes which are in the given group
        """
        return self.nodes_in_all_groups([group_name])

    def nodes_not_in_group(self, group_name):
        """
        Returns a list of nodes not in the given group.

        :param group_name: name of the group to check for
        :return list of nodes which are not in the given group
        """
        return [
            node
            for node in self.nodes
            if not node.in_group(group_name)
        ]

    def nodes_with_bundle(self, bundle_name):
        """
        Returns a list of nodes that do have the given bundle.

        :param bundle_name: name of the bundle to check for
        :return list of nodes which have the given bundle
        """
        return [
            node
            for node in self.nodes
            if bundle_name in names(node.bundles)
        ]

    def nodes_without_bundle(self, bundle_name):
        """
        Returns a list of nodes that do not have the given bundle.

        :param bundle_name: name of the bundle to check for
        :return list of nodes which do not have the given bundle
        """
        return [
            node
            for node in self.nodes
            if bundle_name not in names(node.bundles)
        ]

    def nodes_matching_lambda(self, lambda_str, lambda_workers=None):
        """
        Returns a list of nodes matching the lambda.

        Example:
            nodes = repo.nodes_matching_lambda("lambda:node.metadata_get('foo/magic', 47) < 3")

        :param lambda_str: string to evaluate as python code with `node` being one of the nodes,
            expected to return a value that can be interpreted as boolean
        :param lambda_workers: number of parallel workers used to check lambda condition on every node
        :return list of nodes matching the given lambda
        """
        result_items = parallel_node_eval(
            self.nodes,
            lambda_str,
            lambda_workers,
        ).items()

        return [
            self.get_node(node_name)
            for node_name, result in result_items
            if result
        ]

    def nodes_matching(self, target_strings, lambda_workers=None):
        """
        Returns a list of nodes matching any of the given target-strings. This is the same API that is used by
        all the bw commandlines, i.e. `bw items` or `bw apply` to select which nodes to operate on.

        Example:
            nodes = repo.nodes_matching(['wi-5.s2s', 'wi-5.routing'])

        :param target_strings: expression to select target nodes:
        my_node            # to select a single node
        my_group           # all nodes in this group
        bundle:my_bundle   # all nodes with this bundle
        !bundle:my_bundle  # all nodes without this bundle
        !group:my_group    # all nodes not in this group
        "lambda:node.metadata_get('foo/magic', 47) < 3"
        # all nodes whose metadata["foo"]["magic"] is less than three

        :param lambda_workers: number of parallel workers to check lambda condition on nodes
        :return list of nodes matching any of the given target-strings
        """
        if isinstance(target_strings, str):
            target_strings = [target_strings]

        targets = set()
        for name in target_strings:
            name = name.strip()
            if name.startswith("bundle:"):
                bundle_name = name.split(":", 1)[1]
                targets.update(self.nodes_with_bundle(bundle_name))
            elif name.startswith("!bundle:"):
                bundle_name = name.split(":", 1)[1]
                targets.update(self.nodes_without_bundle(bundle_name))
            elif name.startswith("!group:"):
                group_name = name.split(":", 1)[1]
                targets.update(self.nodes_in_group(group_name))
            elif name.startswith("lambda:"):
                lambda_str = name.split(":", 1)[1]
                targets.update(self.nodes_matching_lambda(lambda_str, lambda_workers))
            else:
                try:
                    targets.add(self.get_node(name))
                except NoSuchNode:
                    try:
                        group = self.get_group(name)
                        targets.update(group.nodes)
                    except NoSuchGroup:
                        raise NoSuchTarget(name)

        return list(targets)

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
                lines = [line.strip() for line in f.readlines()]

                # Ignore empty lines and comments.
                lines = [line for line in lines if line and not line.startswith('#')]

                # "-e some/editable" and "-r other_requirements.txt" are not
                # supported.
                lines = [line for line in lines if not line.startswith('-')]
        except Exception:
            pass
        else:
            if version_info >= VERSION_NEW_PACKAGING:
                _check_requirements(lines)
            else:
                _check_requirements_legacy(lines)

        self.vault = SecretProxy(self)

        # populate bundles
        self.bundle_names = []
        for dir_entry in listdir(self.bundles_dir):
            if validate_name(dir_entry):
                self.bundle_names.append(dir_entry)

        # populate magic strings
        self.get_magic_strings()

        # populate groups
        toml_groups = self.nodes_or_groups_from_dir("groups")
        self.group_dict = {}
        for group_name, group_attrs in self.nodes_or_groups_from_file(self.groups_file, 'groups', toml_groups):
            self.add_group(Group(group_name, attributes=group_attrs, repo=self))

        # populate items
        self.item_classes = list(self.items_from_dir(items.__path__[0]))
        for item_class in self.items_from_dir(self.items_dir):
            self.item_classes.append(item_class)

        # populate nodes
        toml_nodes = self.nodes_or_groups_from_dir("nodes")
        self.node_dict = {}
        for node_name, node_attrs in self.nodes_or_groups_from_file(self.nodes_file, 'nodes', toml_nodes):
            self.add_node(Node(node_name, attributes=node_attrs, repo=self))

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
        self.magic_strings_file = join(self.path, FILENAME_MAGIC_STRINGS)
        self.nodes_file = join(self.path, FILENAME_NODES)

        self.hooks = HooksProxy(self, self.hooks_dir)
        self.libs = LibsProxy(self.libs_dir)
