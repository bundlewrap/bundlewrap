from os.path import join

from .exceptions import ActionFailure, BundleError, RepositoryError
from .utils import get_all_attrs_from_file, LOG
from .utils.text import mark_for_translation as _
from .utils.text import bold, green, red, validate_name, wrap_question
from .utils.ui import ask_interactively


FILENAME_BUNDLE = "bundle.py"


class Action(object):
    """
    A command that is run on a node before or after items are applied.
    """
    def __init__(self, bundle, name, config):
        self.bundle = bundle
        self.name = name
        self.triggered = False

        self.validate_config(bundle, name, config)

        self.command = config['command']
        self.expected_return_code = config.get('expected_return_code', 0)
        self.expected_stderr = config.get('expected_stderr', None)
        self.expected_stdout = config.get('expected_stdout', None)
        self.interactive = config.get('interactive', None)
        self.timing = config.get('timing', "pre")
        self.unless = config.get('unless', "")

    def get_result(self, interactive=False, interactive_default=True):
        if interactive is False and self.interactive is True:
            return None

        if self.unless:
            unless_result = self.bundle.node.run(
                self.unless,
                may_fail=True,
            )
            if unless_result.return_code == 0:
                LOG.debug("{}:action:{}: failed 'unless', not running".format(
                    self.bundle.node.name,
                    self.name,
                ))
                return None

        if (
            interactive and
            self.interactive is not False
            and not ask_interactively(
                wrap_question(self.name, self.command, _("Run action {}?").format(
                    bold(self.name),
                )),
                interactive_default,
            )
        ):
            return None
        try:
            self.run(interactive=interactive)
            return True
        except ActionFailure:
            return False

    def run(self, interactive=False):
        result = self.bundle.node.run(
            self.command,
            may_fail=True,
        )

        if self.expected_return_code is not None and \
                not result.return_code == self.expected_return_code:
            if not interactive:
                LOG.error("{}:action:{}: {}".format(
                    self.bundle.node.name,
                    self.name,
                    red(_("FAILED")),
                ))
            raise ActionFailure(_(
                "wrong return code for action '{}' in bundle '{}': "
                "expected {}, but was {}"
            ).format(
                self.name,
                self.bundle.name,
                self.expected_return_code,
                result.return_code,
            ))

        if self.expected_stderr is not None and \
                result.stderr != self.expected_stderr:
            LOG.error("{}:action:{}: {}".format(
                self.bundle.node.name,
                self.name,
                red(_("FAILED")),
            ))
            raise ActionFailure(_(
                "wrong stderr for action '{}' in bundle '{}'"
            ).format(
                self.name,
                self.bundle.name,
            ))

        if self.expected_stdout is not None and \
                result.stdout != self.expected_stdout:
            LOG.error("{}:action:{}: {}".format(
                self.bundle.node.name,
                self.name,
                red(_("FAILED")),
            ))
            raise ActionFailure(_(
                "wrong stdout for action '{}' in bundle '{}'"
            ).format(
                self.name,
                self.bundle.name,
            ))

        LOG.info("{}:action:{}: {}".format(
            self.bundle.node.name,
            self.name,
            green(_("OK")),
        ))

        return result

    @classmethod
    def validate_config(cls, bundle, name, config):
        if config.get('interactive', None) not in (True, False, None):
            raise BundleError(_(
                "invalid interactive setting for action '{}' in bundle '{}'"
            ).format(name, bundle.name))
        if config.get('timing', "pre") not in (
            'pre',
            'post',
            'triggered',
        ):
            raise BundleError(_(
                "invalid timing for action '{}' in bundle '{}'"
            ).format(name, bundle.name))
        if "command" not in config:
            raise BundleError(_(
                "action '{}' in bundle '{}' has no command set"
            ).format(name, bundle.name))
        unknown_attributes = set(config.keys()).difference(set((
            'command',
            'expected_stderr',
            'expected_stdout',
            'expected_return_code',
            'interactive',
            'timing',
            'unless',
        )))
        if unknown_attributes:
            raise BundleError(_(
                "unknown attributes for action '{}' in bundle '{}': {}"
            ).format(name, bundle.name, ", ".join(unknown_attributes)))


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

        self.bundle_dir = join(self.repo.bundles_dir, self.name)
        self.bundle_file = join(self.bundle_dir, FILENAME_BUNDLE)

        self.action_dict = {}
        self.item_dict = {}

        if self.repo.path != "/dev/null":
            self.read_from_file(self.bundle_file)

    def __getstate__(self):  # pragma: no cover
        """
        Removes cached custom items prior to pickling because their
        classes are loaded dynamically and can't be pickled.
        """
        custom_items = []
        for item_name, item in self.item_dict.iteritems():
            if item.LOADED_FROM_FILE:
                custom_items.append(item_name)
        for item_name in custom_items:
            del self.item_dict[item_name]
        return self.__dict__

    def __repr__(self):
        return "<Bundle '{}' for node '{}'>".format(self.name, self.node.name)

    def __setstate__(self, dict):
        self.__dict__ = dict
        if self.repo.path != "/dev/null":
            self.read_from_file(self.bundle_file, only_custom_items=True)

    @property
    def actions(self):
        return self.action_dict.values()

    def add_action(self, name, config):
        action = Action(self, name, config)
        self.action_dict[name] = action
        return action

    def add_item(self, attribute_name, item_name, config):
        item_class = self.repo.item_classes[attribute_name]
        item = item_class(self, item_name, config)
        self.item_dict[item_name] = item
        return item

    @property
    def items(self):
        return self.item_dict.values()

    def read_from_file(self, filepath, only_custom_items=False):
        bundle_attrs = get_all_attrs_from_file(
            filepath,
            base_env={
                'node': self.node,
                'repo': self.repo,
            },
        )

        if not only_custom_items:
            for action_name, config in bundle_attrs.get('actions', {}).iteritems():
                self.add_action(action_name, config)

        for attribute_name, item_class in self.repo.item_classes.iteritems():
            if not item_class.LOADED_FROM_FILE and only_custom_items:
                continue
            for item_name, config in bundle_attrs.get(attribute_name, {}).iteritems():
                self.add_item(attribute_name, item_name, config)
