def bw_items(repo, args):
    node = repo.get_node(args.node)
    for item in node.items:
        yield str(item)
