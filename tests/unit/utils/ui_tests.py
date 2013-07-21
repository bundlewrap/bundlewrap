from unittest import TestCase

from mock import MagicMock

from blockwart.utils import ui


class AskInteractivelyTest(TestCase):
    """
    Tests blockwart.utils.ui.ask_interactively.
    """
    def test_yes(self):
        get_input = MagicMock(return_value="y")
        self.assertEqual(
            ui.ask_interactively("OHAI?", True, get_input=get_input),
            True,
        )
        get_input.assert_called_once_with("OHAI? [Y/n] ")

    def test_no(self):
        get_input = MagicMock(return_value="n")
        self.assertEqual(
            ui.ask_interactively("OHAI?", True, get_input=get_input),
            False,
        )
        get_input.assert_called_once_with("OHAI? [Y/n] ")

    def test_default_yes(self):
        get_input = MagicMock(return_value="")
        self.assertEqual(
            ui.ask_interactively("OHAI?", True, get_input=get_input),
            True,
        )
        get_input.assert_called_once_with("OHAI? [Y/n] ")

    def test_default_no(self):
        get_input = MagicMock(return_value="")
        self.assertEqual(
            ui.ask_interactively("OHAI?", False, get_input=get_input),
            False,
        )
        get_input.assert_called_once_with("OHAI? [y/N] ")

    def test_invalid_input(self):
        answers = ["wat", "zomg", "\n", "y"]

        def side_effect(*args):
            return answers.pop(0)

        get_input = MagicMock(side_effect=side_effect)
        self.assertEqual(
            ui.ask_interactively("OHAI?", False, get_input=get_input),
            True,
        )
        self.assertEqual(get_input.call_count, 4)
