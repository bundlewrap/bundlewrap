# Deploying from git

The `git_deploy` item lets you deploy the *contents* of a git repository to a node - without requiring the node to have access to that repository or exposing the `.git/` directory to the node.

    directories = {
        # git_deploy will not create this by itself
        "/var/tmp/example": {},
    }

    git_deploy = {
        "/var/tmp/example": {
            'repo': "example",
            'rev': "master",
            'use_xattrs': True,
        },
    }

`git_deploy` items will only upload a tarball with the data from the git repo, no part of the git history is leaked to the node.

Requires git to be installed on the machine running BundleWrap.

<br>

# git_deploy_repos

Put this in a file called git_deploy_repos in your repository root:

    example: /Users/jdoe/Projects/example

This file should also be added to your `.gitignore` if you are sharing that repo with a team. Each team member must provide a mapping of the repo name used in the bundle ("example" in this case) to a local filesystem path with a git repository. It is each user's responsibility to make sure the clone in that location is up to date.

<br>

# Attribute reference

See also: [The list of generic builtin item attributes](../repo/items.py.md#builtin-item-attributes)

<hr>

## repo

The short name of a repo as it appears in `git_deploy_repos`.

Alternatively, it can point directly to a git URL:

    git_deploy = {
        "/var/tmp/example": {
            'repo': "https://github.com/bundlewrap/bundlewrap.git",
            [...]
        },
    }

Note however that this has a performance penalty, as a new clone of that repo has to be made on every run of BundleWrap. (See section "Environment variables" below.)

<br>

## rev

The `rev` attribute can contain anything `git rev-parse` can resolve into a commit hash (branch names, tags, first few characters of full commit hash). Note that you should probably use tags here. *Never* use HEAD (use a branch name like 'master' instead).

<br>

## use_xattrs

BundleWrap needs to store the deployed commit hash on the node. The `use_xattrs` attribute controls how this is done. If set to `True`, the `attr` command on the node is used to store the hash as an extended file system attribute. Since `attr` might not be installed on the node, the default is to place a dotfile in the target directory instead (keep that in mind when deploying websites etc.).

<br>

# Environment variables

## `BW_GIT_DEPLOY_CACHE`

This only affects repositories for which a URL has been specified.

With this env var unset, BundleWrap will clone repos to a temporary directory. This is done once per BundleWrap process and removed automatically when the process terminates.

If you *manually* launch multiple parallel processes of `bw`, each of those will clone the git repo. This can create significant overhead, since they all create redundant copies. You can set `BW_GIT_DEPLOY_CACHE` to an absolute path: All the `bw` processes will use it as a shared cache.

Note: It is not wise to use this option on your workstation. BundleWrap will only ever clone repos, not pull or delete them. This variable is meant as a temporary cache, for example in CI builds, and you will have to clean it up yourself.
