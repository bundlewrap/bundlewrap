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
