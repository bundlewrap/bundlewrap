def make_repo(tmpdir, bundles=None, groups=None, nodes=None):
    bundles = {} if bundles is None else bundles
    groups = {} if groups is None else groups
    nodes = {} if nodes is None else nodes

    bundles_dir = tmpdir.mkdir("bundles")
    for bundle, items in bundles.items():
        bundle_dir = bundles_dir.mkdir(bundle)
        bundlepy = bundle_dir.join("bundle.py")
        bundle_content = ""
        for itemtype, itemconfig in items.items():
            bundle_content += "{} = {}\n".format(itemtype, repr(itemconfig))
        bundlepy.write(bundle_content)

    groupspy = tmpdir.join("groups.py")
    groupspy.write("groups = {}\n".format(repr(groups)))

    nodespy = tmpdir.join("nodes.py")
    nodespy.write("nodes = {}\n".format(repr(nodes)))
