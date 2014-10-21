# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from copy import copy
from os.path import join

from .exceptions import NoSuchBundle, RepositoryError
from .utils import cached_property, get_all_attrs_from_file
from .utils.text import mark_for_translation as _
from .utils.text import validate_name


FILENAME_BUNDLE = "bundle.py"


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

        if not name in self.repo.bundle_names:
            raise NoSuchBundle(_("bundle not found: {}").format(name))

        self.bundle_dir = join(self.repo.bundles_dir, self.name)
        self.bundle_data_dir = join(self.repo.data_dir, self.name)
        self.bundle_file = join(self.bundle_dir, FILENAME_BUNDLE)

    def __getstate__(self):
        """
        Removes cached items prior to pickling because their classed are
        loaded dynamically and can't be pickled.
        """
        state = copy(self.__dict__)
        try:
            del state['_cache']
        except KeyError:
            pass
        return state

    @cached_property
    def bundle_attrs(self):
        return get_all_attrs_from_file(
            self.bundle_file,
            base_env={
                'node': self.node,
                'repo': self.repo,
            },
        )

    @property
    def item_generator_names(self):
        return self.bundle_attrs.get('item_generators', [])

    @cached_property
    def _generated_items(self):
        return self.node._generated_items_for_bundle(self.name)

    @cached_property
    def _static_items(self):
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

    @property
    def items(self):
        for item in self._static_items:
            yield item
        for item in self._generated_items:
            yield item

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
