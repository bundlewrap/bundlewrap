from blockwart.exceptions import ActionFailure, BundleError
from blockwart.items import Item
from blockwart.utils import LOG
from blockwart.utils.ui import ask_interactively
from blockwart.utils.text import mark_for_translation as _
from blockwart.utils.text import bold, green, red, wrap_question


class Action(Item):
    """
    A command that is run on a node before or after items are applied.
    """
    BUNDLE_ATTRIBUTE_NAME = 'actions'
    DEPENDS_STATIC = []
    ITEM_ATTRIBUTES = {
        'command': None,
        'expected_stderr': None,
        'expected_stdout': None,
        'expected_return_code': 0,
        'interactive': None,
    }
    ITEM_TYPE_NAME = 'action'
    REQUIRED_ATTRIBUTES = ['command']

    def get_result(self, interactive=False, interactive_default=True):
        if interactive is False and self.attributes['interactive'] is True:
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
            self.attributes['interactive'] is not False
            and not ask_interactively(
                wrap_question(
                    self.id,
                    self.attributes['command'],
                    _("Run action {}?").format(
                        bold(self.name),
                    ),
                ),
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
            self.attributes['command'],
            may_fail=True,
        )

        if self.attributes['expected_return_code'] is not None and \
                not result.return_code == self.attributes['expected_return_code']:
            if not interactive:
                LOG.error("{}:{}: {}".format(
                    self.bundle.node.name,
                    self.id,
                    red(_("FAILED")),
                ))
            raise ActionFailure(_(
                "wrong return code for action '{}' in bundle '{}': "
                "expected {}, but was {}"
            ).format(
                self.name,
                self.bundle.name,
                self.attributes['expected_return_code'],
                result.return_code,
            ))

        if self.attributes['expected_stderr'] is not None and \
                result.stderr != self.attributes['expected_stderr']:
            LOG.error("{}:{}: {}".format(
                self.bundle.node.name,
                self.id,
                red(_("FAILED")),
            ))
            raise ActionFailure(_(
                "wrong stderr for action '{}' in bundle '{}'"
            ).format(
                self.name,
                self.bundle.name,
            ))

        if self.attributes['expected_stdout'] is not None and \
                result.stdout != self.attributes['expected_stdout']:
            LOG.error("{}:{}: {}".format(
                self.bundle.node.name,
                self.id,
                red(_("FAILED")),
            ))
            raise ActionFailure(_(
                "wrong stdout for action '{}' in bundle '{}'"
            ).format(
                self.name,
                self.bundle.name,
            ))

        LOG.info("{}:{}: {}".format(
            self.bundle.node.name,
            self.id,
            green(_("OK")),
        ))

        return result

    def validate_attributes(self, attributes):
        if attributes.get('interactive', None) not in (True, False, None):
            raise BundleError(_(
                "invalid interactive setting for action '{}' in bundle '{}'"
            ).format(self.name, self.bundle.name))
