from imp import load_source
from os import listdir, mkdir
from os.path import isdir, isfile, join

from . import items
from .exceptions import NoSuchGroup, NoSuchNode, NoSuchRepository, RepositoryError
from .group import Group
from .node import Node
from . import utils
from .utils.text import mark_for_translation as _, validate_name

DIRNAME_BUNDLES = "bundles"
DIRNAME_ITEM_TYPES = "items"
DIRNAME_LIBS = "libs"
FILENAME_GROUPS = "groups.py"
FILENAME_NODES = "nodes.py"

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

RESERVED_ITEM_TYPE_NAMES = ("actions",)


class LibsProxy(object):
    def __init__(self, path):
        self.__module_cache = {}
        self.__path = path

    def __getattr__(self, attrname):
        if attrname not in self.__module_cache:
            filename = attrname + ".py"
            filepath = join(self.__path, filename)
            m = load_source("blockwart.repo.libs.{}".format(attrname), filepath)
            self.__module_cache[attrname] = m
        return self.__module_cache[attrname]


class Repository(object):
    def __init__(self, repo_path, skip_validation=False):
        self.path = repo_path

        self.bundles_dir = join(self.path, DIRNAME_BUNDLES)
        self.items_dir = join(self.path, DIRNAME_ITEM_TYPES)
        self.groups_file = join(self.path, FILENAME_GROUPS)
        self.libs_dir = join(self.path, DIRNAME_LIBS)
        self.nodes_file = join(self.path, FILENAME_NODES)

        self.libs = LibsProxy(self.libs_dir)

        if not skip_validation and not self.is_repo(repo_path):
            raise NoSuchRepository(
                _("'{}' is not a blockwart repository").format(self.path)
            )

    def __getstate__(self):
        """
        Removes cached item classes prior to pickling because they are loaded
        dynamically and can't be pickled.
        """
        try:
            del self._cache['item_classes']
        except:
            pass
        return self.__dict__

    def __repr__(self):
        return "<Repository at '{}'>".format(self.path)

    @staticmethod
    def is_repo(path):
        """
        Validates whether the given path is a blockwart repository.
        """
        try:
            assert isdir(path)
            assert isfile(join(path, "nodes.py"))
            assert isfile(join(path, "groups.py"))
        except AssertionError:
            return False
        return True

    @utils.cached_property
    def bundle_names(self):
        """
        Returns the names of all bundles in this repository.
        """
        for dir_entry in listdir(self.bundles_dir):
            if validate_name(dir_entry):
                yield dir_entry

    @utils.cached_property
    def item_classes(self):
        """
        Looks for Item subclasses in the items directory that ships with
        blockwart and the local items dir of this specific repo.

        An alternative method would involve metaclasses (as Django
        does it), but then it gets very hard to have two separate repos
        in the same process, because both of them would register config
        item classes globally.
        """
        for path in items.__path__ + [self.items_dir]:
            if not isdir(path):
                continue
            for filename in listdir(path):
                filepath = join(path, filename)
                if not filename.endswith(".py") or \
                        not isfile(filepath) or \
                        filename.startswith("_"):
                    continue
                for name, obj in \
                        utils.get_all_attrs_from_file(filepath).iteritems():
                    if obj == items.Item or name.startswith("_"):
                        continue
                    try:
                        if issubclass(obj, items.Item):
                            if obj.ITEM_TYPE_NAME in RESERVED_ITEM_TYPE_NAMES:
                                raise RepositoryError(_(
                                    "'{}' is a reserved item type name"
                                ).format(obj.ITEM_TYPE_NAME))
                            else:
                                yield obj
                    except TypeError:
                        pass

    def create(self):
        """
        Sets up initial content for a repository.
        """
        for filename, content in INITIAL_CONTENT.iteritems():
            with open(join(self.path, filename), 'w') as f:
                f.write(content.strip() + "\n")
        mkdir(self.bundles_dir)
        mkdir(self.items_dir)

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

    @utils.cached_property
    def group_dict(self):
        try:
            flat_group_dict = utils.getattr_from_file(
                self.groups_file,
                'groups',
            )
        except KeyError:
            raise RepositoryError(_(
                "{} must define a 'groups' variable"
            ).format(self.groups_file))
        groups = {}
        for groupname, infodict in flat_group_dict.iteritems():
            if groupname in utils.names(self.nodes):
                raise RepositoryError(_("you cannot have a node and a group "
                                        "both named '{}'").format(groupname))
            groups[groupname] = Group(self, groupname, infodict)
        return groups

    @property
    def groups(self):
        result = list(self.group_dict.values())
        result.sort()
        return result

    def groups_for_node(self, node):
        for group in self.groups:
            if node in group.nodes:
                yield group

    @utils.cached_property
    def node_dict(self):
        try:
            flat_node_dict = utils.getattr_from_file(
                self.nodes_file,
                'nodes',
            )
        except KeyError:
            raise RepositoryError(
                _("{} must define a 'nodes' variable").format(
                    self.nodes_file,
                )
            )
        nodes = {}
        for nodename, infodict in flat_node_dict.iteritems():
            nodes[nodename] = Node(self, nodename, infodict)
        return nodes

    @property
    def nodes(self):
        result = list(self.node_dict.values())
        result.sort()
        return result
