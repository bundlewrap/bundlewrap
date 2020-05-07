from ..utils.cmdline import get_target_nodes
from ..utils.text import mark_for_translation as _, red
from ..utils.ui import io


def bw_diff(repo, args):
    target_nodes = get_target_nodes(repo, args['target'], adhoc_nodes=args['adhoc_nodes'])
    if args['branch']:
        pass
    else:
        if len(target_nodes) != 2:
            io.stdout(_(
                "{x} Exactly two nodes must be selected when comparing within "
                "the same branch"
            ).format(x=red("!!!")))
            exit(1)
