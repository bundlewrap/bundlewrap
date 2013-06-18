def bw_nodes(repo, args):
    for node in repo.nodes:
        if args.show_hostnames:
            yield node.hostname
        else:
            yield node.name
