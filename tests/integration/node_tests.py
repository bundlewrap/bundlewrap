from unittest import TestCase

from blockwart.node import Node


class NodeTest(TestCase):
    def test_run_stdout(self):
        n = Node(None, 'localhost', {})
        r = n.run("echo -n 47")
        self.assertEqual(r.stdout, "47")
