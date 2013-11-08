from unittest import TestCase

from mock import MagicMock, patch

from blockwart.cmdline import repo


class DebugTest(TestCase):
    """
    Tests blockwart.cmdline.repo.bw_repo_debug.
    """
    @patch('blockwart.cmdline.repo.interact')
    def test_interactive(self, interact):
        args = MagicMock()
        args.node = None
        repo_obj = MagicMock()
        repo_obj.path = "/dev/null"
        repo_obj_validated = MagicMock()
        with patch(
                'blockwart.cmdline.repo.Repository',
                return_value=repo_obj_validated,
        ) as repo_class:
            repo.bw_repo_debug(repo_obj, args)

            repo_class.assert_called_with(
                repo_obj.path,
                skip_validation=False,
            )
            interact.assert_called_with(
                repo.DEBUG_BANNER,
                local={'repo': repo_obj_validated},
            )

    @patch('blockwart.cmdline.repo.interact')
    def test_interactive_node(self, interact):
        args = MagicMock()
        args.node = "node1"
        args.itemid = None
        node = MagicMock()
        node.name = args.node
        repo_obj = MagicMock()
        repo_obj.path = "/dev/null"
        repo_obj_validated = MagicMock()
        repo_obj_validated.get_node = MagicMock(return_value=node)
        with patch(
                'blockwart.cmdline.repo.Repository',
                return_value=repo_obj_validated,
        ):
            repo.bw_repo_debug(repo_obj, args)
            interact.assert_called_with(
                repo.DEBUG_BANNER_NODE,
                local={
                    'node': node,
                    'repo': repo_obj_validated,
                },
            )


class PlotTest(TestCase):
    """
    Tests blockwart.cmdline.repo.bw_repo_plot.
    """
    def test_output(self):
        item1 = MagicMock()
        item1.DEPENDS_STATIC = []
        item1.depends = []
        item1.id = "type1:item1"

        item2 = MagicMock()
        item2.DEPENDS_STATIC = []
        item2.depends = []
        item2.id = "type1:item2"

        item3 = MagicMock()
        item3.DEPENDS_STATIC = []
        item3.depends = ["type1:item1"]
        item3.id = "type2:item1"

        item4 = MagicMock()
        item4.DEPENDS_STATIC = ["type2:"]
        item4.depends = []
        item4.id = "type3:item1"

        bundle1 = MagicMock()
        bundle1.name = "bundle1"
        bundle1.items = [item1, item2, item3]

        bundle2 = MagicMock()
        bundle2.name = "bundle2"
        bundle2.items = [item4]

        node = MagicMock()
        node.bundles = [bundle1, bundle2]
        node.items = [item1, item2, item3, item4]
        node.name = "node"

        args = MagicMock()
        args.node = "node"
        args.depends_static = True
        args.depends_regular = True
        args.depends_auto = True

        rep = MagicMock()
        rep.get_node.return_value = node

        self.assertEqual(
            "\n".join(list(repo.bw_repo_plot(rep, args))),
            "digraph blockwart\n"
            "{\n"
            "rankdir = LR\n"
            "graph [color=\"#303030\"; "
            "fontname=Helvetica; "
            "penwidth=2; "
            "shape=box; "
            "style=\"rounded,dashed\"]\n"
            "node [color=\"#303030\"; "
            "fillcolor=\"#303030\"; "
            "fontcolor=white; "
            "fontname=Helvetica; "
            "shape=box; "
            "style=\"rounded,filled\"]\n"
            "edge [arrowhead=vee]\n"
            "subgraph cluster_0\n"
            "{\n"
            "label = \"bundle1\"\n"
            "\"type1:item1\"\n"
            "\"type1:item2\"\n"
            "\"type2:item1\"\n"
            "}\n"
            "subgraph cluster_1\n"
            "{\n"
            "label = \"bundle2\"\n"
            "\"type3:item1\"\n"
            "}\n"
            "\"type1:\" -> \"type1:item1\" [color=\"#6BB753\",penwidth=2]\n"
            "\"type1:\" -> \"type1:item2\" [color=\"#6BB753\",penwidth=2]\n"
            "\"type3:\" -> \"type3:item1\" [color=\"#6BB753\",penwidth=2]\n"
            "\"type2:\" -> \"type2:item1\" [color=\"#6BB753\",penwidth=2]\n"
            "\"type2:item1\" -> \"type1:item1\" [color=\"#C24948\",penwidth=2]\n"
            "\"type3:item1\" -> \"type2:\" [color=\"#3991CC\",penwidth=2]\n"
            "fontsize = 28\n"
            "label = \"node\"\n"
            "labelloc = \"t\"\n"
            "}"
            ,
        )
