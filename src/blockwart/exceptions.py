class NoSuchGroup(Exception):
    """
    Raised when a group of unknown name is requested.
    """
    pass


class NoSuchNode(Exception):
    """
    Raised when a node of unknown name is requested.
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


class UsageException(Exception):
    """
    Raised when command line options don't make sense.
    """
    pass
