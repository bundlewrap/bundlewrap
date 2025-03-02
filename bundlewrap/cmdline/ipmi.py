from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import blue, bold
from ..utils.text import mark_for_translation as _
from ..utils.text import red, red_unless_zero, yellow
from ..utils.ui import io


def bw_ipmi(repo, args):
    node = repo.get_node(args['node'])
    result = node.run_ipmitool(args['command'])

    for line in result.stdout_text.splitlines():
        io.stdout("{x}  {node}  {line}".format(
            x=yellow("»"),
            node=bold(node.name),
            line=line,
        ))

    for line in result.stderr_text.splitlines():
        io.stderr("{x}  {node}  {line}".format(
            x=red("!"),
            node=bold(node.name),
            line=line,
        ))

    stats_table = [
        [bold(_("node")), bold(_("exit code"))],
        ROW_SEPARATOR,
        [node.name, red_unless_zero(result.return_code)],
    ]

    for line in render_table(stats_table):
        io.stdout("{x} {line}".format(x=blue("i"), line=line))
