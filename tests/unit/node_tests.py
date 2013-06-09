from unittest import TestCase

from blockwart.node import Node


class NodeTest(TestCase):
    def test_hostname_defaults(self):
        n = Node(None, 'node1', {})
        self.assertEqual(n.hostname, 'node1')
        n = Node(None, 'node2', {'hostname': 'node2.example.com'})
        self.assertEqual(n.hostname, 'node2.example.com')
