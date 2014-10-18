# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from mock import MagicMock, patch

from bundlewrap.cmdline import run
from bundlewrap.operations import RunResult
from bundlewrap.repo import HooksProxy


class FakeRepo(object):
    def __init__(self):
        self.hooks = HooksProxy("/invalid/path/404/not/found")


class FakeNode(object):
    def __init__(self, nodename):
        self.name = nodename
        self.repo = FakeRepo()
        self.result = RunResult()
        self.result.stdout = "[node] out: some\n[node] out: output"
        self.result.stderr = "[node] err: some errors"
        self.result.return_code = 47

    def run(self, *args, **kwargs):
        return self.result


class RunTest(TestCase):
    """
    Tests bundlewrap.cmdline.run.bw_run.
    """
    @patch('bundlewrap.cmdline.run.get_target_nodes')
    def test_single_node_fail(self, get_target_nodes):
        args = {}
        args['command'] = "foo"
        args['may_fail'] = False
        args['node_workers'] = 2
        args['sudo'] = True
        args['target'] = "node1"

        node = FakeNode("node1")
        get_target_nodes.return_value = [node]

        output = list(run.bw_run(MagicMock(), args))

        self.assertTrue(output[0].startswith("[node1] ✘ failed after "))
        self.assertTrue(output[0].endswith("s (return code 47)"))

    @patch('bundlewrap.cmdline.run.get_target_nodes')
    def test_group_success(self, get_target_nodes):
        args = {}
        args['command'] = "foo"
        args['may_fail'] = False
        args['node_workers'] = 2
        args['sudo'] = True
        args['target'] = "node1,node2"

        node1 = FakeNode("node1")
        node1.result.return_code = 0
        node2 = FakeNode("node2")
        node2.result.return_code = 0
        get_target_nodes.return_value = [node1, node2]

        output = list(run.bw_run(MagicMock(), args))
        self.assertTrue("completed successfully after" in output[0])
        self.assertTrue("completed successfully after" in output[1])
        self.assertEqual(len(output), 2)
