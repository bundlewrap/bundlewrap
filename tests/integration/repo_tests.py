from blockwart import repo
from blockwart.exceptions import RepositoryError

from ..unit.repo_tests import RepoTest


class NodeGroupNameClashTest(RepoTest):
    def test_node_group_name_clash(self):
        r = repo.Repository(self.tmpdir, skip_validation=True)
        with open(r.groups_file, 'w') as f:
            f.write("groups = {'highlander': {}}")
        with open(r.nodes_file, 'w') as f:
            f.write("nodes = {'highlander': {}}")
        with self.assertRaises(RepositoryError):
            r.groups
