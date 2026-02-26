class BundlewrapError(Exception):
    """
    Base class for all BundleWrap-specific exceptions.
    """
    pass

class DontCache(BundlewrapError):
    """
    Used in the cached_property decorator to temporily prevent caching
    the returned result
    """
    def __init__(self, obj):
        self.obj = obj


class FaultUnavailable(BundlewrapError):
    """
    Raised when a Fault object cannot be resolved.
    """
    pass


class MetadataUnavailable(BundlewrapError):
    """
    Raised when a Metadata key cannot be resolved.
    """
    def __init__(self, path=None):
        self.path = path

    def __str__(self):
        if self.path is None:
            return "path: <unknown>"
        return f"path: {'/'.join(self.path)}"
    
    def __repr__(self):
        if self.path is None:
            return "<MetadataUnavailable>"
        return f"<MetadataUnavailable path={'/'.join(self.path)}>"

class GracefulApplyException(BundlewrapError):
    """
    Raised when a problem has been encountered in `bw apply`, but a more
    verbose error has already been printed.
    """
    pass


class ItemSkipped(BundlewrapError):
    """
    Raised when an item is skipped during `bw verify`.
    """
    pass

class NoSuchBundle(BundlewrapError):
    """
    Raised when a bundle of unknown name is requested.
    """
    pass


class NoSuchGroup(BundlewrapError):
    """
    Raised when a group of unknown name is requested.
    """
    pass


class NoSuchItem(BundlewrapError):
    """
    Raised when an item of unknown name is requested.
    """
    pass


class NoSuchNode(BundlewrapError):
    """
    Raised when a node of unknown name is requested.
    """
    pass


class NoSuchTarget(BundlewrapError):
    """
    Raised when a target matches neither bundle nor group, item or node.
    """
    
    def __init__(self, target):
        self.target = target

    def __repr__(self):
        return f"<NoSuchTarget {self.target}>"

    def __str__(self):
        return self.target


class RemoteException(BundlewrapError):
    """
    Raised when a shell command on a node fails.
    """
    pass


class TransportException(BundlewrapError):
    """
    Raised when there is an error on the transport layer, e.g. SSH failures.
    """
    pass


class RepositoryError(BundlewrapError):
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


class InvalidMagicStringException(RepositoryError):
    """
    Raised when an invalid magic string is encountered.
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


class SkipNode(BundlewrapError):
    """
    Can be raised by hooks to skip a node.
    """
    pass


class TemplateError(RepositoryError):
    """
    Raised when an error occurs while rendering a template.
    """
    pass


class UsageException(BundlewrapError):
    """
    Raised when command line options don't make sense.
    """
    pass


class NodeLockedException(BundlewrapError):
    """
    Raised when a node is already locked during an 'apply' run.
    """
    pass

class ValidatorError(BundlewrapError):
    """
    Raised when a validator fails.
    """
    pass