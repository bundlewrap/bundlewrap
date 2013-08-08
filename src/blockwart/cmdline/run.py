from datetime import datetime

from ..utils import LOG
from ..utils.cmdline import get_target_nodes
from ..utils.text import mark_for_translation as _


def _format_output(nodename, stream, msg):
    # remove "[host] out: " prefix from Fabric
    needle = ": "
    msg = msg[msg.find(needle) + len(needle):]
    return "{} ({}): {}".format(nodename, stream, msg)

def bw_run(repo, args):
    for node in get_target_nodes(repo, args.target):
        start = datetime.now()
        result = node.run(
            args.command,
            may_fail=args.may_fail,
            stderr=lambda msg: LOG.warn(_format_output(node.name, "stderr", msg)),
            stdout=lambda msg: LOG.info(_format_output(node.name, "stdout", msg)),
            sudo=args.sudo,
        )
        end = datetime.now()
        duration = end - start
        if result.return_code == 0:
            yield _("{}: completed successfully after {}s").format(
                node.name,
                duration.total_seconds(),
            )
        else:
            if not args.verbose:
                # show output of failed command if not already shown by -v
                for stream, content in (
                    ("stdout", result.stdout),
                    ("stderr", result.stderr),
                ):
                    for line in content.splitlines():
                        yield "{} ({}): {}".format(node.name, stream, line)
            yield _("{}: failed after {}s (return code {})").format(
                node.name,
                duration.total_seconds(),
                result.return_code,
            )
