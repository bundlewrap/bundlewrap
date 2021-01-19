from collections import OrderedDict
from sys import version_info

from ..metadata import METADATA_TYPES, deepcopy_metadata, validate_metadata, value_at_key_path
from .dicts import ATOMIC_TYPES, map_dict_keys, merge_dict


UNMERGEABLE = tuple(METADATA_TYPES) + tuple(ATOMIC_TYPES.values())


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
            {} if version_info >= (3, 7) else OrderedDict(),  # node/groups
            {} if version_info >= (3, 7) else OrderedDict(),  # reactors
            {} if version_info >= (3, 7) else OrderedDict(),  # defaults
        )
        self._cached_partitions = {}

    def get(self, path):
        """
        Get the value at the given path, merging all layers together.
        """
        result = None
        undef = True

        for part_index, partition in enumerate(self._partitions):
            # prefer cached partitions if available
            partition = self._cached_partitions.get(part_index, partition)
            for layer in reversed(list(partition.values())):
                try:
                    value = value_at_key_path(layer, path)
                except KeyError:
                    pass
                else:
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
            raise KeyError('/'.join(path))
        else:
            return deepcopy_metadata(result['data'])

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
                    except KeyError:
                        pass
                    else:
                        blame.setdefault(path, []).append(identifier)
        return blame

    def pop_layer(self, partition_index, identifier):
        try:
            return self._partitions[partition_index].pop(identifier)
        except (KeyError, IndexError):
            return {}

    def set_layer(self, partition_index, identifier, new_layer):
        validate_metadata(new_layer)
        self._partitions[partition_index][identifier] = new_layer

    def cache_partition(self, partition_index):
        self._cached_partitions[partition_index] = {
            'merged layers': self.as_dict(partitions=[partition_index]),
        }
