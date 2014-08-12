class ActionFailure(Exception):
    """
    Raised when an action failes to meet the expected rcode/output.
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


class NoSuchPlugin(Exception):
    """
    Raised when a plugin of unknown name is requested.
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


class NoSuchRepository(RepositoryError):
    """
    Raised when trying to get a Repository object from a directory that
    is not in fact a repository.
    """
    pass


class PluginError(RepositoryError):
    """
    Indicates an error related to a plugin.
    """
    pass


class PluginLocalConflict(PluginError):
    """
    Raised when a plugin tries to overwrite locally-modified files.
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


class WorkerException(Exception):
    """
    Raised when a worker process has encountered an exception while
    executing.
    """
    def __init__(self, task_id, wrapped_exception, traceback):
        self.task_id = task_id
        self.traceback = traceback
        self.wrapped_exception = wrapped_exception

    def __str__(self):
        output = "\n\n+----- traceback from worker ------\n|\n"
        for line in self.traceback.strip().split("\n"):
            output += "|  {}\n".format(line)
        output += "|\n+----------------------------------\n"
        return output


class NodeAlreadyLockedException(Exception):
    """
    Raised when a node is already locked during an 'apply' run.
    """
    pass
