from ..exceptions import NoSuchNode


def bw_run(repo, args):
    try:
        targets = [repo.get_node(args.target)]
    except NoSuchNode:
        targets = repo.get_group(args.target).nodes
    for node in targets:
        result = node.run(args.command, sudo=args.sudo)
        if result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                yield "{} (stdout): {}".format(node.name, line)
        if result.stderr.strip():
            for line in result.stderr.strip().split("\n"):
                yield "{} (stderr): {}".format(node.name, line)
