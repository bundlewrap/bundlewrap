class DontCache(Exception):
    """
    Used in the cached_property decorator to temporily prevent caching
    the returned result
    """
    def __init__(self, obj):
        self.obj = obj


class FaultUnavailable(Exception):
    """
    Raised when a Fault object cannot be resolved.
    """
    pass


class GracefulApplyException(Exception):
    """
    Raised when a problem has been encountered in `bw apply`, but a more
    verbose error has already been printed.
    """
    pass


class ItemSkipped(Exception):
    """
    Raised when an item is skipped during `bw verify`.
    """
    pass

class NoSuchBundle(Exception):
    """
    Raised when a bundle of unknown name is requested.
    """
    pass


class NoSuchGroup(Exception):
    """
    Raised when a group of unknown name is requested.
    """
    pass


class NoSuchItem(Exception):
    """
    Raised when an item of unknown name is requested.
    """
    pass


class NoSuchNode(Exception):
    """
    Raised when a node of unknown name is requested.
    """
    pass


class RemoteException(Exception):
    """
    Raised when a shell command on a node fails.
    """
    pass


class TransportException(Exception):
    """
    Raised when there is an error on the transport layer, e.g. SSH failures.
    """
    pass


class RepositoryError(Exception):
    """
    Indicates that somethings is wrong with the current repository.
    """
    pass


class BundleError(RepositoryError):
    """
    Indicates an error in a bundle.
    """
    pass


class ItemDependencyError(RepositoryError):
    """
    Indicates a problem with item dependencies (e.g. loops).
    """
    pass


class NoSuchRepository(RepositoryError):
    """
    Raised when trying to get a Repository object from a directory that
    is not in fact a repository.
    """
    pass


class MetadataPersistentKeyError(RepositoryError):
    """
    Raised when metadata reactors keep raising KeyErrors indefinitely.
    """
    pass


class MissingRepoDependency(RepositoryError):
    """
    Raised when a dependency from requirements.txt is missing.
    """
    pass


class SkipNode(Exception):
    """
    Can be raised by hooks to skip a node.
    """
    pass


class TemplateError(RepositoryError):
    """
    Raised when an error occurs while rendering a template.
    """
    pass


class UsageException(Exception):
    """
    Raised when command line options don't make sense.
    """
    pass


class NodeLockedException(Exception):
    """
    Raised when a node is already locked during an 'apply' run.
    """
    pass
