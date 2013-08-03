from ..utils.cmdline import get_target_nodes

def bw_run(repo, args):
    for node in get_target_nodes(repo, args.target):
        result = node.run(args.command, sudo=args.sudo)
        if result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                yield "{} (stdout): {}".format(node.name, line)
        if result.stderr.strip():
            for line in result.stderr.strip().split("\n"):
                yield "{} (stderr): {}".format(node.name, line)
