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


class RemoteException(Exception):
    """
    Raised when a shell command on a node fails.
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


class WorkerException(Exception):
    """
    Raised when a worker process has encountered an exception while
    executing.
    """
    def __init__(self, nested_exception, traceback):
        self.nested_exception = nested_exception
        self.traceback = traceback

    def __str__(self):
        return ("\n\n--- BEGIN NESTED TRACEBACK ---\n"
                "\n{}\n{}"
                "\n--- END NESTED TRACEBACK ---\n".format(
                    self.traceback,
                    self.nested_exception,
                ))
