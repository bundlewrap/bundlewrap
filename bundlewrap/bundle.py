# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import exists, join

from .exceptions import NoSuchBundle, RepositoryError
from .metadata import DEFAULTS, DONE, RUN_ME_AGAIN, OVERWRITE
from .utils import cached_property, get_all_attrs_from_file
from .utils.text import mark_for_translation as _
from .utils.text import validate_name
from .utils.ui import io


FILENAME_BUNDLE = "items.py"
FILENAME_METADATA = "metadata.py"


def metadata_processor(func):
    """
    Decorator that tags metadata processors.
    """
    func.__is_a_metadata_processor = True
    return func


class Bundle(object):
    """
    A collection of config items, bound to a node.
    """
    def __init__(self, node, name):
        self.name = name
        self.node = node
        self.repo = node.repo

        if not validate_name(name):
            raise RepositoryError(_("invalid bundle name: {}").format(name))

        if name not in self.repo.bundle_names:
            raise NoSuchBundle(_("bundle not found: {}").format(name))

        self.bundle_dir = join(self.repo.bundles_dir, self.name)
        self.bundle_data_dir = join(self.repo.data_dir, self.name)
        self.bundle_file = join(self.bundle_dir, FILENAME_BUNDLE)
        self.metadata_file = join(self.bundle_dir, FILENAME_METADATA)

    def __lt__(self, other):
        return self.name < other.name

    @cached_property
    def bundle_attrs(self):
        if not exists(self.bundle_file):
            return {}
        else:
            with io.job(_("  {node}  {bundle}  collecting items...").format(
                node=self.node.name,
                bundle=self.name,
            )):
                return get_all_attrs_from_file(
                    self.bundle_file,
                    base_env={
                        'node': self.node,
                        'repo': self.repo,
                    },
                )

    @cached_property
    def items(self):
        for item_class in self.repo.item_classes:
            for item_name, item_attrs in self.bundle_attrs.get(
                item_class.BUNDLE_ATTRIBUTE_NAME,
                {},
            ).items():
                yield self.make_item(
                    item_class.BUNDLE_ATTRIBUTE_NAME,
                    item_name,
                    item_attrs,
                )

    def make_item(self, attribute_name, item_name, item_attrs):
        for item_class in self.repo.item_classes:
            if item_class.BUNDLE_ATTRIBUTE_NAME == attribute_name:
                return item_class(self, item_name, item_attrs)
        raise RuntimeError(
            _("bundle '{bundle}' tried to generate item '{item}' from "
              "unknown attribute '{attr}'").format(
                attr=attribute_name,
                bundle=self.name,
                item=item_name,
            )
        )

    @cached_property
    def metadata_processors(self):
        with io.job(_("  {node}  {bundle}  collecting metadata processors...").format(
            node=self.node.name,
            bundle=self.name,
        )):
            if not exists(self.metadata_file):
                return []
            result = []
            for name, attr in get_all_attrs_from_file(
                self.metadata_file,
                base_env={
                    'DEFAULTS': DEFAULTS,
                    'DONE': DONE,
                    'RUN_ME_AGAIN': RUN_ME_AGAIN,
                    'OVERWRITE': OVERWRITE,
                    'metadata_processor': metadata_processor,
                    'node': self.node,
                    'repo': self.repo,
                },
            ).items():
                if getattr(attr, '__is_a_metadata_processor', False):
                    result.append(attr)
            return result
