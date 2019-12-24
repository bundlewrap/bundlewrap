# -*- coding: utf-8 -*-
from __future__ import unicode_literals

VERSION = (3, 6, 2)
VERSION_STRING = ".".join([str(v) for v in VERSION])


class Metadata(dict):
    def __init__(self, dict={}, parent=None, key=None):
        super().__setattr__('parent', parent)
        super().__setattr__('key', key)
        self.update(dict)
    
    def __getattr__(self, key):
        value = self.get(key)
        if value:
            return Metadata(value) if isinstance(value, dict) else value
        else:
            return NoMetadata(parent=self, key=key)
    
    def __setattr__(self, key, value):
        if key == 'parent' or key == 'key':
            return super().__setattr__(key, value)
        else:
            self[key] = value
            self.assign_to_parent()
            return value
    
    def assign_to_parent(self):
        if self.parent != None:
            self.parent[self.key] = self
            self.parent.assign_to_parent()


class NoMetadata(Metadata):
    def __bool__(self):
        return self.parent != None

    def __str__(self):
        return ''
