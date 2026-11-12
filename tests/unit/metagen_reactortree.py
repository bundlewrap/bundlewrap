from bundlewrap.metagen import ReactorTree


def test_reactors_for():
    tree = ReactorTree()
    tree.add("r_node", ("node",))
    tree.add("r_foo", ("node", "foo"))
    tree.add("r_foo_bar", ("node", "foo", "bar"))
    tree.add("r_foo_bar2", ("node", "foo", "bar"))
    tree.add("r_baz", ("node", "baz"))
    tree.add("r_other", ("other", "foo"))
    assert set(tree.reactors_for(("node", "foo"))) == {"r_node", "r_foo", "r_foo_bar", "r_foo_bar2"}
    assert set(tree.reactors_for(("node", "foo", "bar", "x"))) == {
        "r_node", "r_foo", "r_foo_bar", "r_foo_bar2",
    }
    assert set(tree.reactors_for(("node", "baz"))) == {"r_node", "r_baz"}
    assert set(tree.reactors_for(("node", "nope"))) == {"r_node"}
    assert set(tree.reactors_for(("other",))) == {"r_other"}
    assert set(tree.reactors_for()) == {
        "r_node", "r_foo", "r_foo_bar", "r_foo_bar2", "r_baz", "r_other",
    }


def test_root_reactor():
    tree = ReactorTree()
    tree.add("r_all", ())
    tree.add("r_foo", ("foo",))
    assert set(tree.reactors_for(("bar",))) == {"r_all"}
    assert set(tree.reactors_for(("foo", "x"))) == {"r_all", "r_foo"}
