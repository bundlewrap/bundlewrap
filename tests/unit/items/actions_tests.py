from unittest import TestCase

from mock import MagicMock, patch

from blockwart.items.actions import Action
from blockwart.exceptions import ActionFailure, BundleError


class ActionInitTest(TestCase):
    """
    Tests initialization of blockwart.items.actions.Action.
    """
    def test_ok(self):
        Action(MagicMock(), "action", { 'command': "/bin/true" })

    def test_no_command(self):
        with self.assertRaises(BundleError):
            Action(MagicMock(), "action", {})

    def test_unknown_attr(self):
        with self.assertRaises(BundleError):
            Action(MagicMock(), "action", {
                'command': "/bin/true",
                'foo': "bar",
            })

    def test_invalid_interactive(self):
        with self.assertRaises(BundleError):
            Action(MagicMock(), "action", {
                'command': "/bin/true",
                'interactive': "maybe",
            })


class ActionRunTest(TestCase):
    """
    Tests blockwart.items.actions.Action.run.
    """
    def test_ok(self):
        run_result = MagicMock()
        run_result.return_code = 0
        run_result.stderr = ""
        run_result.stdout = ""

        bundle = MagicMock()
        bundle.node.run.return_value = run_result

        action = Action(bundle, "action", { 'command': "/bin/true" })

        self.assertEqual(action.run(), run_result)

    def test_return_code(self):
        run_result = MagicMock()
        run_result.return_code = 1
        run_result.stderr = ""
        run_result.stdout = ""

        bundle = MagicMock()
        bundle.node.run.return_value = run_result

        action = Action(bundle, "action", { 'command': "/bin/true" })

        with self.assertRaises(ActionFailure):
            action.run()

    def test_stderr(self):
        run_result = MagicMock()
        run_result.return_code = 0
        run_result.stderr = "47"
        run_result.stdout = ""

        bundle = MagicMock()
        bundle.node.run.return_value = run_result

        action = Action(bundle, "action", {
            'command': "/bin/true",
            'expected_stderr': "48"
        })

        with self.assertRaises(ActionFailure):
            action.run()

    def test_stdout(self):
        run_result = MagicMock()
        run_result.return_code = 0
        run_result.stderr = ""
        run_result.stdout = "47"

        bundle = MagicMock()
        bundle.node.run.return_value = run_result

        action = Action(bundle, "action", {
            'command': "/bin/true",
            'expected_stdout': "48"
        })

        with self.assertRaises(ActionFailure):
            action.run()


class ActionGetResultTest(TestCase):
    """
    Tests blockwart.items.actions.Action.get_result.
    """
    def test_fail_unless(self):
        unless_result = MagicMock()
        unless_result.return_code = 0

        bundle = MagicMock()
        bundle.node.run.return_value = unless_result

        action = Action(bundle, "action", { 'command': "/bin/true", 'unless': "true" })
        self.assertEqual(
            action.get_result(),
            Action.STATUS_SKIPPED,
        )

    def test_skip_noninteractive(self):
        action = Action(MagicMock(), "action", { 'command': "/bin/true", 'interactive': True })
        self.assertEqual(
            action.get_result(interactive=False),
            Action.STATUS_SKIPPED,
        )

    @patch('blockwart.items.actions.ask_interactively', return_value=False)
    def test_declined_interactive(self, ask_interactively):
        action = Action(MagicMock(), "action", { 'command': "/bin/true" })
        self.assertEqual(
            action.get_result(interactive=True),
            Action.STATUS_SKIPPED,
        )

    def test_ok(self):
        action = Action(MagicMock(), "action", { 'command': "/bin/true" })
        action.run = MagicMock(return_value=None)
        self.assertEqual(
            action.get_result(interactive=False),
            Action.STATUS_ACTION_SUCCEEDED,
        )

    def test_fail(self):
        action = Action(MagicMock(), "action", { 'command': "/bin/false" })
        action.run = MagicMock(side_effect=ActionFailure)
        self.assertEqual(
            action.get_result(interactive=False),
            Action.STATUS_FAILED,
        )
