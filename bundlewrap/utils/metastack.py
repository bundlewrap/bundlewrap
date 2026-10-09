from ..exceptions import MetadataUnavailable
from ..metadata import METADATA_TYPES, deepcopy_metadata, validate_metadata, value_at_key_path
from .dicts import ATOMIC_TYPES, map_dict_keys, merge_dict


UNMERGEABLE = tuple(METADATA_TYPES) + tuple(ATOMIC_TYPES.values())
_MISSING = object()


def _value_at_key_path_or_missing(layer, path):
    """
    Like value_at_key_path(), but returns _MISSING instead of raising
    MetadataUnavailable. Most layers do not contain most paths, so
    avoiding an exception per miss matters in Metastack.get().
    """
    value = layer
    for depth, key in enumerate(path):
        if type(value) is not dict:
            # dict subclasses may implement __getitem__/__missing__,
            # let value_at_key_path() handle them exactly as before
            if depth and not isinstance(value, dict):
                return _MISSING
            try:
                return value_at_key_path(value, path[depth:])
            except MetadataUnavailable:
                return _MISSING
        value = value.get(key, _MISSING)
        if value is _MISSING:
            return _MISSING
    return value


class Metastack:
    """
    Holds a number of metadata layers. When laid on top of one another,
    these layers form complete metadata for a node. Each layer comes
    from one particular source of metadata: a bundle default, a group,
    the node itself, or a metadata reactor. Metadata reactors are unique
    in their ability to revise their own layer each time they are run.
    """

    def __init__(self):
        self._partitions = (
            # We rely heavily on insertion order in these dicts.
            {},  # node/groups
            {},  # reactors
            {},  # defaults
        )
        self._cached_partitions = {}
        # merged (but not yet copied) results of get(), by path
        self._get_cache = {}

    def get(self, path):
        """
        Get the value at the given path, merging all layers together.
        """
        cache_key = tuple(path)
        try:
            value = self._get_cache[cache_key]
        except KeyError:
            value = self._get_cache[cache_key] = self._merge_path(path)
        if value is _MISSING:
            raise MetadataUnavailable(path)
        return deepcopy_metadata(value)

    def _merge_path(self, path):
        result = None
        undef = True

        for part_index, partition in enumerate(self._partitions):
            # prefer cached partitions if available
            partition = self._cached_partitions.get(part_index, partition)
            for layer in reversed(partition.values()):
                value = _value_at_key_path_or_missing(layer, path)
                if value is not _MISSING:
                    if undef:
                        # First time we see anything. If we can't merge
                        # it anyway, then return early.
                        if isinstance(value, UNMERGEABLE):
                            return value
                        result = {'data': value}
                        undef = False
                    else:
                        result = merge_dict({'data': value}, result)

        if undef:
            return _MISSING
        else:
            return result['data']

    def as_dict(self, partitions=None):
        final_dict = {}

        if partitions is None:
            partitions = tuple(range(len(self._partitions)))
        else:
            partitions = sorted(partitions)

        for part_index in partitions:
            # prefer cached partitions if available
            partition = self._cached_partitions.get(part_index, self._partitions[part_index])
            for layer in reversed(list(partition.values())):
                final_dict = merge_dict(layer, final_dict)

        return final_dict

    def as_blame(self):
        keymap = map_dict_keys(self.as_dict())
        blame = {}
        for path in keymap:
            for partition in self._partitions:
                for identifier, layer in partition.items():
                    try:
                        value_at_key_path(layer, path)
                    except MetadataUnavailable:
                        pass
                    else:
                        blame.setdefault(path, []).append(identifier)
        return blame

    def pop_layer(self, partition_index, identifier):
        self._get_cache.clear()
        try:
            return self._partitions[partition_index].pop(identifier)
        except (KeyError, IndexError):
            return {}

    def set_layer(self, partition_index, identifier, new_layer):
        validate_metadata(new_layer)
        self._get_cache.clear()
        self._partitions[partition_index][identifier] = new_layer

    def cache_partition(self, partition_index):
        self._get_cache.clear()
        self._cached_partitions[partition_index] = {
            'merged layers': self.as_dict(partitions=[partition_index]),
        }
