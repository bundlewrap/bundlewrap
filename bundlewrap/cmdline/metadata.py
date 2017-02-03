# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from json import dumps

from ..metadata import MetadataJSONEncoder, value_at_key_path
from ..utils.cmdline import get_node
from ..utils.text import force_text
from ..utils.ui import io


def bw_metadata(repo, args):
    node = get_node(repo, args['node'], adhoc_nodes=args['adhoc_nodes'])
    for line in dumps(
        value_at_key_path(node.metadata, args['keys']),
        cls=MetadataJSONEncoder,
        indent=4,
        sort_keys=True,
    ).splitlines():
        io.stdout(force_text(line))
