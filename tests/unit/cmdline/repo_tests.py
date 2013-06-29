from unittest import TestCase

from mock import MagicMock, patch

from blockwart.cmdline import repo


class DebugTest(TestCase):
    """
    Tests blockwart.cmdline.repo.bw_repo_debug.
    """
    @patch('blockwart.cmdline.repo.interact')
    def test_interactive(self, interact):
        repo_obj = MagicMock()
        repo_obj.path = "/dev/null"
        repo_obj_validated = MagicMock()
        with patch(
                'blockwart.cmdline.repo.Repository',
                return_value=repo_obj_validated,
        ) as repo_class:
            repo.bw_repo_debug(repo_obj, MagicMock())

            repo_class.assert_called_with(
                repo_obj.path,
                skip_validation=False,
            )
            interact.assert_called_with(
                repo.DEBUG_BANNER,
                local={'repo': repo_obj_validated},
            )
