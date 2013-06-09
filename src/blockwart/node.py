class Node(object):
    def __init__(self, repo, name, infodict):
        self.name = name
        self.repo = repo
        if 'hostname' in infodict:
            self.hostname = infodict['hostname']
        else:
            self.hostname = self.name
