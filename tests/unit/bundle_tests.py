from unittest import TestCase

from mock import MagicMock, patch

from blockwart.bundle import Action, Bundle
from blockwart.items import Item
from blockwart.exceptions import ActionFailure, BundleError, RepositoryError
from blockwart.utils import names


class ActionInitTest(TestCase):
    """
    Tests initialization of blockwart.bundle.Action.
    """
    def test_ok(self):
        Action(MagicMock(), "action", { 'command': "/bin/true" })

    def test_no_command(self):
        with self.assertRaises(BundleError):
            Action(MagicMock(), "action", {})

    def test_invalid_timing(self):
        with self.assertRaises(BundleError):
            Action(MagicMock(), "action", {
                'command': "/bin/true",
                'timing': "tomorrow",
            })


class ActionRunTest(TestCase):
    """
    Tests blockwart.bundle.Action.run.
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

    def test_stderr_static(self):
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

    def test_stderr_callable(self):
        run_result = MagicMock()
        run_result.return_code = 0
        run_result.stderr = "47"
        run_result.stdout = ""

        bundle = MagicMock()
        bundle.node.run.return_value = run_result

        action = Action(bundle, "action", {
            'command': "/bin/true",
            'expected_stderr': lambda s: "48" in s,
        })

        with self.assertRaises(ActionFailure):
            action.run()

    def test_stdout_static(self):
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

    def test_stdout_callable(self):
        run_result = MagicMock()
        run_result.return_code = 0
        run_result.stderr = ""
        run_result.stdout = "47"

        bundle = MagicMock()
        bundle.node.run.return_value = run_result

        action = Action(bundle, "action", {
            'command': "/bin/true",
            'expected_stdout': lambda s: "48" in s,
        })

        with self.assertRaises(ActionFailure):
            action.run()


class BundleInitTest(TestCase):
    """
    Tests initialization of blockwart.bundle.Bundle.
    """
    @patch('blockwart.bundle.validate_name', return_value=False)
    def test_bad_bundle_name(self, *args):
        with self.assertRaises(RepositoryError):
            Bundle(MagicMock(), "name")


class BundleActionsTest(TestCase):
    """
    Tests blockwart.bundle.Bundle.actions.
    """
    @patch('blockwart.bundle.get_all_attrs_from_file', return_value={
        'actions': {'name1': { 'command': "" }, 'name2': { 'command': "" }},
        'attr2': {'name3': {}},
    })
    def test_actions(self, *args):
        node = MagicMock()
        node.repo.bundle_names = ("mybundle",)
        b = Bundle(node, "mybundle")
        self.assertEqual(
            set([b.actions[0].name, b.actions[1].name]),
            set(['name1', 'name2']),
        )


class BundleItemsTest(TestCase):
    """
    Tests blockwart.bundle.Bundle.items.
    """
    @patch('blockwart.bundle.get_all_attrs_from_file', return_value={
        'attr1': {'name1': {}, 'name2': {}},
        'attr2': {'name3': {}},
    })
    def test_items(self, *args):
        class MyItem(Item):
            BUNDLE_ATTRIBUTE_NAME = 'attr1'
            ITEM_TYPE_NAME = 'mystuff'
        node = MagicMock()
        node.repo.bundle_names = ("mybundle",)
        node.repo.item_classes = (MyItem,)
        b = Bundle(node, "mybundle")
        self.assertEqual(set(names(b.items)), set(('name1', 'name2')))
