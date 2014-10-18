from unittest import TestCase

from mock import MagicMock

from bundlewrap.cmdline import plot
from bundlewrap.items import Item


class PlotTest(TestCase):
    """
    Tests bundlewrap.cmdline.repo.bw_repo_plot.
    """
    def test_output(self):
        class FakeItem1(Item):
            BUNDLE_ATTRIBUTE_NAME = "fakes1"
            ITEM_TYPE_NAME = "type1"

        class FakeItem2(Item):
            BUNDLE_ATTRIBUTE_NAME = "fakes1"
            ITEM_TYPE_NAME = "type2"

        class FakeItem3(Item):
            BUNDLE_ATTRIBUTE_NAME = "fakes1"
            ITEM_TYPE_NAME = "type3"

        class FakeBundle(object):
            bundle_dir = "/dev/null"
            bundle_data_dir = "/dev/null"
            node = None

        item1 = FakeItem1(FakeBundle(), "item1", {})
        item2 = FakeItem1(FakeBundle(), "item2", {})
        item3 = FakeItem2(FakeBundle(), "item1", {})
        item3.needs = ["type1:item1"]

        item4 = FakeItem3(FakeBundle(), "item1", {})
        item4.NEEDS_STATIC = ["type2:"]

        bundle1 = MagicMock()
        bundle1.name = "bundle1"
        bundle1.items = [item1, item2, item3]
        for item in bundle1.items:
            item.bundle = bundle1

        bundle2 = MagicMock()
        bundle2.name = "bundle2"
        bundle2.items = [item4]
        for item in bundle2.items:
            item.bundle = bundle2

        node = MagicMock()
        node.bundles = [bundle1, bundle2]
        node.items = [item1, item2, item3, item4]
        node.name = "node"

        args = {}
        args['node'] = "node"
        args['cluster'] = True
        args['depends_concurrency'] = True
        args['depends_static'] = True
        args['depends_regular'] = True
        args['depends_reverse'] = True
        args['depends_auto'] = True

        rep = MagicMock()
        rep.get_node.return_value = node

        self.assertEqual(
            "\n".join(list(plot.bw_plot_node(rep, args))),
            "digraph bundlewrap\n"
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
            "label = \"bundle2\"\n"
            "\"bundle:bundle2\"\n"
            "\"type3:item1\"\n"
            "}\n"
            "subgraph cluster_1\n"
            "{\n"
            "label = \"bundle1\"\n"
            "\"bundle:bundle1\"\n"
            "\"type1:item1\"\n"
            "\"type1:item2\"\n"
            "\"type2:item1\"\n"
            "}\n"
            "\"bundle:bundle2\" -> \"type3:item1\" [color=\"#6BB753\",penwidth=2]\n"
            "\"bundle:bundle1\" -> \"type1:item1\" [color=\"#6BB753\",penwidth=2]\n"
            "\"bundle:bundle1\" -> \"type1:item2\" [color=\"#6BB753\",penwidth=2]\n"
            "\"bundle:bundle1\" -> \"type2:item1\" [color=\"#6BB753\",penwidth=2]\n"
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
