from os.path import join


def bw_generate_completions(repo, args):
    compl_file = join(repo.path, '.bw_shell_completion_targets')

    targets = {f'node:{node.name}' for node in repo.nodes}
    targets |= {f'group:{group.name}' for group in repo.groups}
    targets |= {f'!group:{group.name}' for group in repo.groups}
    targets |= {f'bundle:{bundle}' for bundle in repo.bundle_names}
    targets |= {f'!bundle:{bundle}' for bundle in repo.bundle_names}

    with open(compl_file, 'w') as f:
        f.write('\n'.join(sorted(targets)))
