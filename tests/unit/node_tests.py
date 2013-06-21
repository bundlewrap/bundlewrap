from unittest import TestCase

from mock import MagicMock, patch

from blockwart.group import Group
from blockwart.node import Node
from blockwart.utils import names


class NodeTest(TestCase):
    """
    Tests blockwart.node.Node.
    """
    def test_bundles(self):
        repo = MagicMock()
        repo.bundle_names = ("bundle1", "bundle2", "bundle3")
        n = Node(repo, "node1", {})
        g1 = Group(None, "group1", {'bundles': ("bundle1", "bundle2")})
        g2 = Group(None, "group2", {'bundles': ("bundle3",)})
        with patch('tests.unit.node_tests.Node.groups', new=(g1, g2)):
            self.assertEqual(
                tuple(names(n.bundles)),
                ("bundle1", "bundle2", "bundle3"),
            )

    def test_hostname_defaults(self):
        n = Node(None, "node1", {})
        self.assertEqual(n.hostname, "node1")
        n = Node(None, "node2", {'hostname': "node2.example.com"})
        self.assertEqual(n.hostname, "node2.example.com")
