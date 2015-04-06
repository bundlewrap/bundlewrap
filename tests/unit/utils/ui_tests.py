# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

try:
    from unittest.mock import call, MagicMock
except ImportError:
    from mock import call, MagicMock

from bundlewrap.utils import ui


class LineBufferTest(TestCase):
    """
    Tests bundlewrap.utils.ui.LineBuffer.
    """
    def test_buffer(self):
        target = MagicMock()
        buffer = ui.LineBuffer(target)
        buffer.write(b"aaaaaa\nbbb")
        buffer.write(b"bb\ncccc\n")
        buffer.write(b"ddd\nee")
        buffer.write(b"\n")
        buffer.write(b"f\n")

        self.assertEqual(
            target.call_args_list,
            [
                call(b"aaaaaa\n"),
                call(b"bbbbb\n"),
                call(b"cccc\n"),
                call(b"ddd\n"),
                call(b"ee\n"),
                call(b"f\n"),
            ],
        )


class AskInteractivelyTest(TestCase):
    """
    Tests bundlewrap.utils.ui.ask_interactively.
    """
    def test_yes(self):
        get_input = MagicMock(return_value="y")
        self.assertEqual(
            ui.ask_interactively("OHAI?", True, get_input=get_input),
            True,
        )
        get_input.assert_called_once_with(b"OHAI? [Y/n] ")

    def test_no(self):
        get_input = MagicMock(return_value="n")
        self.assertEqual(
            ui.ask_interactively("OHAI?", True, get_input=get_input),
            False,
        )
        get_input.assert_called_once_with(b"OHAI? [Y/n] ")

    def test_default_yes(self):
        get_input = MagicMock(return_value="")
        self.assertEqual(
            ui.ask_interactively("OHAI?", True, get_input=get_input),
            True,
        )
        get_input.assert_called_once_with(b"OHAI? [Y/n] ")

    def test_default_no(self):
        get_input = MagicMock(return_value="")
        self.assertEqual(
            ui.ask_interactively("OHAI?", False, get_input=get_input),
            False,
        )
        get_input.assert_called_once_with(b"OHAI? [y/N] ")

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
