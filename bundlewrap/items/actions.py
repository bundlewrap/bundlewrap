from datetime import datetime

from bundlewrap.exceptions import BundleError
from bundlewrap.items import format_comment, Item
from bundlewrap.utils import Fault
from bundlewrap.utils.ui import io
from bundlewrap.utils.text import mark_for_translation as _
from bundlewrap.utils.text import blue, bold, wrap_question


class ActionFailure(Exception):
    """
    Raised when an action failes to meet the expected rcode/output.
    """

    def __init__(self, failed_expectations):
        self.failed_expectations = failed_expectations


class Action(Item):
    """
    A command that is run on a node.
    """
    BUNDLE_ATTRIBUTE_NAME = 'actions'
    ITEM_ATTRIBUTES = {
        'command': None,
        'data_stdin': None,
        'expected_stderr': None,
        'expected_stdout': None,
        'expected_return_code': {0},
        'interactive': None,
    }
    ITEM_TYPE_NAME = 'action'
    REQUIRED_ATTRIBUTES = ['command']

    def _get_result(
        self,
        autoonly_selector="",
        autoskip_selector="",
        my_soft_locks=(),
        other_peoples_soft_locks=(),
        interactive=False,
        interactive_default=True,
        show_diff=True,
    ):
        if self._faults_missing_for_attributes:
            if self.error_on_missing_fault:
                self._raise_for_faults()
            else:
                io.debug(_(
                    "skipping {item} on {node} because it is missing faults "
                    "for these attributes: {attrs} "
                    "(most of the time this means you're missing "
                    "a required key in your .secrets.cfg)"
                ).format(
                    attrs=", ".join(sorted(self._faults_missing_for_attributes)),
                    item=self.id,
                    node=self.node.name,
                ))
                return (self.STATUS_SKIPPED, self.SKIP_REASON_FAULT_UNAVAILABLE, None, None)

        if not self.covered_by_autoonly_selector(autoonly_selector):
            io.debug(_(
                "autoonly does not match {item} on {node}"
            ).format(item=self.id, node=self.node.name))
            return (self.STATUS_SKIPPED, self.SKIP_REASON_CMDLINE, None, None)

        if self.covered_by_autoskip_selector(autoskip_selector):
            io.debug(_(
                "autoskip matches {item} on {node}"
            ).format(item=self.id, node=self.node.name))
            return (self.STATUS_SKIPPED, self.SKIP_REASON_CMDLINE, None, None)

        if self._skip_with_soft_locks(my_soft_locks, other_peoples_soft_locks):
            return (self.STATUS_SKIPPED, self.SKIP_REASON_SOFTLOCK, None, None)

        if interactive is False and self.attributes['interactive'] is True:
            return (self.STATUS_SKIPPED, self.SKIP_REASON_INTERACTIVE_ONLY, None, None)

        for item in self._precedes_items:
            if item._triggers_preceding_items(interactive=interactive):
                io.debug(_(
                    "preceding item {item} on {node} has been triggered by {other_item}"
                ).format(item=self.id, node=self.node.name, other_item=item.id))
                self.has_been_triggered = True
                break
            else:
                io.debug(_(
                    "preceding item {item} on {node} has NOT been triggered by {other_item}"
                ).format(item=self.id, node=self.node.name, other_item=item.id))

        if self.triggered and not self.has_been_triggered:
            io.debug(_("skipping {} because it wasn't triggered").format(self.id))
            return (self.STATUS_SKIPPED, self.SKIP_REASON_NO_TRIGGER, None, None)

        if self.unless:
            with io.job(_("{node}  {bundle}  {item}  checking 'unless' condition").format(
                bundle=bold(self.bundle.name),
                item=self.id,
                node=bold(self.node.name),
            )):
                unless_result = self.bundle.node.run(
                    self.unless,
                    may_fail=True,
                )
            if unless_result.return_code == 0:
                io.debug(_("{node}:{bundle}:action:{name}: failed 'unless', not running").format(
                    bundle=self.bundle.name,
                    name=self.name,
                    node=self.bundle.node.name,
                ))
                return (self.STATUS_SKIPPED, self.SKIP_REASON_UNLESS, None, None)

        question_body = ""
        if self.attributes['data_stdin'] is not None:
            question_body += "<" + _("data") + "> | "
        question_body += self.attributes['command']
        if self.comment:
            question_body += format_comment(self.comment)

        if (
            interactive and
            self.attributes['interactive'] is not False and
            not io.ask(
                wrap_question(
                    self.id,
                    question_body,
                    _("Run action {}?").format(
                        bold(self.name),
                    ),
                    prefix="{x} {node} ".format(
                        node=bold(self.node.name),
                        x=blue("?"),
                    ),
                ),
                interactive_default,
                epilogue="{x} {node}".format(
                    node=bold(self.node.name),
                    x=blue("?"),
                ),
            )
        ):
            return (self.STATUS_SKIPPED, self.SKIP_REASON_INTERACTIVE, None, None)
        try:
            self.run()
            return (self.STATUS_ACTION_SUCCEEDED, None, None, None)
        except ActionFailure as exc:
            return (self.STATUS_FAILED, exc.failed_expectations, None, None)

    def apply(self, *args, **kwargs):
        return self.get_result(*args, **kwargs)

    def cdict(self):
        raise AttributeError(_("actions don't have cdicts"))

    def get_result(self, *args, **kwargs):
        self.node.repo.hooks.action_run_start(
            self.node.repo,
            self.node,
            self,
        )
        start_time = datetime.now()

        result = self._get_result(*args, **kwargs)

        self.node.repo.hooks.action_run_end(
            self.node.repo,
            self.node,
            self,
            duration=datetime.now() - start_time,
            status=result[0],
        )

        return result

    def run(self):
        if self.attributes['data_stdin'] is not None:
            data_stdin = self.attributes['data_stdin']
            # Allow users to use either a string/unicode object or raw
            # bytes -- or Faults.
            if isinstance(data_stdin, Fault):
                data_stdin = data_stdin.value
            if type(data_stdin) is not bytes:
                data_stdin = data_stdin.encode('UTF-8')
        else:
            data_stdin = None

        with io.job(_("{node}  {bundle}  {item}").format(
            bundle=bold(self.bundle.name),
            item=self.id,
            node=bold(self.node.name),
        )):
            result = super().run(
                self.attributes['command'],
                data_stdin=data_stdin,
                may_fail=True,
            )

        failed_expectations = ({}, {}, [])

        if self.attributes['expected_return_code'] is not None and \
                result.return_code not in self.attributes['expected_return_code']:
            failed_expectations[0][_("return code")] = str(self.attributes['expected_return_code'])
            failed_expectations[1][_("return code")] = str(result.return_code)
            failed_expectations[2].append(_("return code"))

        if self.attributes['expected_stderr'] is not None and \
                result.stderr_text != self.attributes['expected_stderr']:
            failed_expectations[0][_("stderr")] = self.attributes['expected_stderr']
            failed_expectations[1][_("stderr")] = result.stderr_text
            failed_expectations[2].append(_("stderr"))

        if self.attributes['expected_stdout'] is not None and \
                result.stdout_text != self.attributes['expected_stdout']:
            failed_expectations[0][_("stdout")] = self.attributes['expected_stdout']
            failed_expectations[1][_("stdout")] = result.stdout_text
            failed_expectations[2].append(_("stdout"))

        if failed_expectations[2]:
            raise ActionFailure(failed_expectations)

        return result

    def patch_attributes(self, attributes):
        if isinstance(attributes.get('expected_return_code'), int):
            attributes['expected_return_code'] = {attributes['expected_return_code']}
        return attributes

    @classmethod
    def validate_attributes(cls, bundle, item_id, attributes):
        if attributes.get('interactive', None) not in (True, False, None):
            raise BundleError(_(
                "invalid interactive setting for action '{item}' in bundle '{bundle}'"
            ).format(item=item_id, bundle=bundle.name))

    def verify(self):
        if self.unless and self.cached_unless_result:
            return self.cached_unless_result, None, None
        else:
            raise NotImplementedError
