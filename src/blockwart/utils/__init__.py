import cProfile
import hashlib
from inspect import isgenerator
import logging
import pstats

__GETATTR_CACHE = {}
__GETATTR_NODEFAULT = "very_unlikely_default_value"


LOG = logging.getLogger('blockwart')


class PrintProfiler(object):
    """
    Will print profiling information.

    Usage:

        with PrintProfiler():
            [code goes here]
    """
    def __enter__(self):
        self.pr = cProfile.Profile()
        self.pr.enable()

    def __exit__(self, type, value, traceback):
        self.pr.disable()
        pstats.Stats(self.pr).sort_stats('cumulative').print_stats()


def cached_property(prop):
    """
    A replacement for the property decorator that will only compute the
    attribute's value on the first call and serve cached copy from then
    on.
    """
    def cache_wrapper(self):
        if not hasattr(self, "_cache"):
            self._cache = {}
        if not prop.func_name in self._cache:
            return_value = prop(self)
            if isgenerator(return_value):
                return_value = tuple(return_value)
            self._cache[prop.func_name] = return_value
        return self._cache[prop.func_name]
    return property(cache_wrapper)


def get_file_contents(path):
    with open(path) as f:
        content = f.read()
    return content


def get_all_attrs_from_file(path, cache_read=True, cache_write=True,
                            base_env=None):
    """
    Reads all 'attributes' (if it were a module) from a source
    file.
    """
    if base_env is None:
        base_env = {}
    if path not in __GETATTR_CACHE or not cache_read:
        source = get_file_contents(path)
        env = base_env.copy()
        exec(source, env)
        if cache_write:
            __GETATTR_CACHE[path] = env
    else:
        env = __GETATTR_CACHE[path]
    return env


def getattr_from_file(path, attrname, cache_read=True, cache_write=True,
                      default=__GETATTR_NODEFAULT,
                      ):
    """
    Reads a specific 'attribute' (if it were a module) from a source
    file.
    """
    env = get_all_attrs_from_file(path, cache_read=cache_read,
                                  cache_write=cache_write)
    if default == __GETATTR_NODEFAULT:
        return env[attrname]
    else:
        return env.get(attrname, default)


def graph_for_items(
    title,
    items,
    cluster=True,
    concurrency=True,
    static=True,
    regular=True,
    reverse=True,
    auto=True,
):
    yield "digraph blockwart"
    yield "{"

    # Print subgraphs *below* each other
    yield "rankdir = LR"

    # Global attributes
    yield ("graph [color=\"#303030\"; "
                  "fontname=Helvetica; "
                  "penwidth=2; "
                  "shape=box; "
                  "style=\"rounded,dashed\"]")
    yield ("node [color=\"#303030\"; "
                 "fillcolor=\"#303030\"; "
                 "fontcolor=white; "
                 "fontname=Helvetica; "
                 "shape=box; "
                 "style=\"rounded,filled\"]")
    yield "edge [arrowhead=vee]"

    item_ids = []
    for item in items:
        item_ids.append(item.id)

    if cluster:
        # Define which items belong to which bundle
        bundle_number = 0
        bundles_seen = []
        for item in items:
            if item.bundle is None or item.bundle.name in bundles_seen:
                continue
            yield "subgraph cluster_{}".format(bundle_number)
            bundle_number += 1
            yield "{"
            yield "label = \"{}\"".format(item.bundle.name)
            yield "\"bundle:{}\"".format(item.bundle.name)
            for bitem in item.bundle.items:
                if bitem.id in item_ids:
                    yield "\"{}\"".format(bitem.id)
            yield "}"
            bundles_seen.append(item.bundle.name)

    # Define dependencies between items
    for item in items:
        if static:
            for dep in item.DEPENDS_STATIC:
                if dep in item_ids:
                    yield "\"{}\" -> \"{}\" [color=\"#3991CC\",penwidth=2]".format(item.id, dep)

        if regular:
            for dep in item.depends:
                if dep in item_ids:
                    yield "\"{}\" -> \"{}\" [color=\"#C24948\",penwidth=2]".format(item.id, dep)

        if auto:
            for dep in item._deps:
                if dep in item._concurrency_deps:
                    if concurrency:
                        yield "\"{}\" -> \"{}\" [color=\"#714D99\",penwidth=2]".format(item.id, dep)
                elif dep in item._reverse_deps:
                    if reverse:
                        yield "\"{}\" -> \"{}\" [color=\"#D18C57\",penwidth=2]".format(item.id, dep)
                elif dep not in item.DEPENDS_STATIC and dep not in item.depends:
                    if dep in item_ids:
                        yield "\"{}\" -> \"{}\" [color=\"#6BB753\",penwidth=2]".format(item.id, dep)

    # Global graph title
    yield "fontsize = 28"
    yield "label = \"{}\"".format(title)
    yield "labelloc = \"t\""
    yield "}"


def names(obj_list):
    """
    Iterator over the name properties of a given list of objects.

    repo.nodes          will give you node objects
    names(repo.nodes)   will give you node names
    """
    for obj in obj_list:
        yield obj.name


def sha1(data):
    """
    Returns hex SHA1 hash for input.
    """
    hasher = hashlib.sha1()
    hasher.update(data)
    return hasher.hexdigest()
