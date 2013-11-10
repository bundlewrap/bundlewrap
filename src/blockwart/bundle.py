from os.path import join

from .exceptions import ActionFailure, BundleError, RepositoryError
from .utils import cached_property, get_all_attrs_from_file, LOG
from .utils.text import green, mark_for_translation as _, red, validate_name

FILENAME_BUNDLE = "bundle.py"


class Action(object):
    """
    A command that is run on a node before or after items are applied.
    """
    def __init__(self, bundle, name, config):
        self.bundle = bundle
        self.name = name

        self.validate_config(bundle, name, config)

        self.command = config['command']
        self.expected_return_code = config.get('expected_return_code', 0)
        self.expected_stderr = config.get('expected_stderr', lambda s: True)
        self.expected_stdout = config.get('expected_stdout', lambda s: True)
        self.timing = config.get('timing', "pre")

    def run(self):
        result = self.bundle.node.run(
            self.command,
            may_fail=True,
        )

        if not result.return_code == self.expected_return_code:
            LOG.warn("{}:action:{}: {}".format(
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

        if callable(self.expected_stderr):
            stderr_correct = self.expected_stderr(result.stderr)
        else:
            stderr_correct = result.stderr == self.expected_stderr
        if not stderr_correct:
            LOG.warn("{}:action:{}: {}".format(
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

        if callable(self.expected_stdout):
            stdout_correct = self.expected_stdout(result.stdout)
        else:
            stdout_correct = result.stdout == self.expected_stdout
        if not stdout_correct:
            LOG.warn("{}:action:{}: {}".format(
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
        if config.get('timing', "pre") not in ("pre", "post"):
            raise BundleError(_(
                "invalid timing for action '{}' in bundle '{}'"
            ).format(name, bundle.name))
        if "command" not in config:
            raise BundleError(_(
                "action '{}' in bundle '{}' has no command set"
            ).format(name, bundle.name))


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
            raise RepositoryError(_("bundle not found: {}").format(name))

        self.bundle_dir = join(self.repo.bundles_dir, self.name)
        self.bundle_file = join(self.bundle_dir, FILENAME_BUNDLE)

    def __getstate__(self):
        """
        Removes cached items prior to pickling because their classed are
        loaded dynamically and can't be pickled.
        """
        try:
            del self._cache['items']
        except:
            pass
        return self.__dict__

    @cached_property
    def _bundle_attrs(self):
        return get_all_attrs_from_file(
            self.bundle_file,
            base_env={
                'node': self.node,
                'repo': self.repo,
            },
        )

    @cached_property
    def actions(self):
        bundle_actions = self._bundle_attrs.get('actions', {})
        for name, config in bundle_actions.iteritems():
            yield Action(self, name, config)

    @cached_property
    def items(self):
        for item_class in self.repo.item_classes:
            if item_class.BUNDLE_ATTRIBUTE_NAME not in self._bundle_attrs:
                continue
            for name, attrs in self._bundle_attrs.get(
                    item_class.BUNDLE_ATTRIBUTE_NAME,
                    {},
            ).iteritems():
                yield item_class(self, name, attrs)
