# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from sys import version_info


class UnicodeException(Exception):
    def __init__(self, msg=""):
        if version_info >= (3, 0):
            super(UnicodeException, self).__init__(msg)
        else:
            super(UnicodeException, self).__init__(msg.encode('utf-8'))


class ActionFailure(UnicodeException):
    """
    Raised when an action failes to meet the expected rcode/output.
    """
    pass


class DontCache(Exception):
    """
    Used in the cached_property decorator to temporily prevent caching
    the returned result
    """
    def __init__(self, obj):
        self.obj = obj


class FaultUnavailable(UnicodeException):
    """
    Raised when a Fault object cannot be resolved.
    """
    pass


class NoSuchBundle(UnicodeException):
    """
    Raised when a bundle of unknown name is requested.
    """
    pass


class NoSuchGroup(UnicodeException):
    """
    Raised when a group of unknown name is requested.
    """
    pass


class NoSuchItem(UnicodeException):
    """
    Raised when an item of unknown name is requested.
    """
    pass


class NoSuchNode(UnicodeException):
    """
    Raised when a node of unknown name is requested.
    """
    pass


class NoSuchPlugin(UnicodeException):
    """
    Raised when a plugin of unknown name is requested.
    """
    pass


class RemoteException(UnicodeException):
    """
    Raised when a shell command on a node fails.
    """
    pass


class RepositoryError(UnicodeException):
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


class MissingRepoDependency(RepositoryError):
    """
    Raised when a dependency from requirements.txt is missing.
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


class UsageException(UnicodeException):
    """
    Raised when command line options don't make sense.
    """
    pass


class NodeLockedException(Exception):
    """
    Raised when a node is already locked during an 'apply' run.
    """
    pass
