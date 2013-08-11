from ..utils import names


def bw_nodes(repo, args):
    for node in repo.nodes:
        line = ""
        if args.show_hostnames:
            line += node.hostname
        else:
            line += node.name
        if args.show_groups:
            line += ": " + ", ".join(names(node.groups))
        yield line
