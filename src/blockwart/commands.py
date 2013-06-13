def run(repo, target, command):
    node = repo.get_node(target)
    return node.run(command).stdout.strip()
