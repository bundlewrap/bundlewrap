from datetime import datetime

from bundlewrap.exceptions import ActionFailure, BundleError
from bundlewrap.items import Item, ItemStatus
from bundlewrap.utils import LOG
from bundlewrap.utils.ui import ask_interactively
from bundlewrap.utils.text import mark_for_translation as _
from bundlewrap.utils.text import bold, wrap_question


class Action(Item):
    """
    A command that is run on a node.
    """
    BUNDLE_ATTRIBUTE_NAME = 'actions'
    ITEM_ATTRIBUTES = {
        'command': None,
        'expected_stderr': None,
        'expected_stdout': None,
        'expected_return_code': 0,
        'interactive': None,
    }
    ITEM_TYPE_NAME = 'action'
    REQUIRED_ATTRIBUTES = ['command']

    def _get_result(self, interactive=False, interactive_default=True):
        if interactive is False and self.attributes['interactive'] is True:
            return self.STATUS_SKIPPED

        if self.triggered and not self.has_been_triggered:
            LOG.debug(_("skipping {} because it wasn't triggered").format(self.id))
            return self.STATUS_SKIPPED

        if self.unless:
            unless_result = self.bundle.node.run(
                self.unless,
                may_fail=True,
            )
            if unless_result.return_code == 0:
                LOG.debug(_("{node}:{bundle}:action:{name}: failed 'unless', not running").format(
                    bundle=self.bundle.name,
                    name=self.name,
                    node=self.bundle.node.name,
                ))
                return self.STATUS_SKIPPED

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
            return self.STATUS_SKIPPED
        try:
            self.run(interactive=interactive)
            return self.STATUS_ACTION_SUCCEEDED
        except ActionFailure:
            return self.STATUS_FAILED

    def get_result(self, interactive=False, interactive_default=True):
        self.node.repo.hooks.action_run_start(
            self.node.repo,
            self.node,
            self,
        )
        start_time = datetime.now()

        status_code = self._get_result(interactive, interactive_default)
        if status_code == Item.STATUS_SKIPPED:
            status = ItemStatus(correct=False, skipped=True)
        elif status_code == Item.STATUS_ACTION_SUCCEEDED:
            status = ItemStatus()
        else:
            status = ItemStatus(correct=False)

        self.node.repo.hooks.action_run_end(
            self.node.repo,
            self.node,
            self,
            duration=datetime.now() - start_time,
            status=status,
        )

        return status_code

    def run(self, interactive=False):
        result = self.bundle.node.run(
            self.attributes['command'],
            may_fail=True,
        )

        if self.attributes['expected_return_code'] is not None and \
                not result.return_code == self.attributes['expected_return_code']:
            raise ActionFailure(_(
                "wrong return code for action '{action}' in bundle '{bundle}': "
                "expected {ecode}, but was {rcode}"
            ).format(
                action=self.name,
                bundle=self.bundle.name,
                ecode=self.attributes['expected_return_code'],
                rcode=result.return_code,
            ))

        if self.attributes['expected_stderr'] is not None and \
                result.stderr != self.attributes['expected_stderr']:
            raise ActionFailure(_(
                "wrong stderr for action '{action}' in bundle '{bundle}'"
            ).format(
                action=self.name,
                bundle=self.bundle.name,
            ))

        if self.attributes['expected_stdout'] is not None and \
                result.stdout != self.attributes['expected_stdout']:
            raise ActionFailure(_(
                "wrong stdout for action '{action}' in bundle '{bundle}'"
            ).format(
                action=self.name,
                bundle=self.bundle.name,
            ))

        return result

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if attributes.get('interactive', None) not in (True, False, None):
            raise BundleError(_(
                "invalid interactive setting for action '{item}' in bundle '{bundle}'"
            ).format(item=item_id, bundle=bundle.name))
