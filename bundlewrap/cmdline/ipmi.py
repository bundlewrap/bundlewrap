from ..concurrency import WorkerPool
from ..utils.cmdline import get_target_nodes
from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import blue, bold, error_summary, format_duration, green
from ..utils.text import mark_for_translation as _
from ..utils.text import red, red_unless_zero, yellow
from ..utils.ui import io


def bw_ipmi(repo, args):
    errors = []
    target_nodes = get_target_nodes(repo, args['targets'], args['node_workers'])
    pending_nodes = target_nodes.copy()
    io.progress_set_total(len(pending_nodes))

    results = {}

    def tasks_available():
        return bool(pending_nodes)

    def next_task():
        node = pending_nodes.pop()
        return {
            'target': node.run_ipmitool,
            'task_id': node.name,
            'kwargs': {
                'command': args['command'],
                'log_output': True,
            },
        }

    def handle_result(task_id, return_value, duration):
        io.progress_advance()
        results[task_id] = return_value

    def handle_exception(task_id, exception, traceback):
        io.progress_advance()
        msg = "{}  {}".format(bold(task_id), exception)
        io.stderr(traceback)
        io.stderr(repr(exception))
        io.stderr("{} {}".format(red("!"), msg))
        errors.append(msg)

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_result=handle_result,
        handle_exception=handle_exception,
        pool_id="ipmi",
        workers=args['node_workers'],
    )
    worker_pool.run()

    stats_table = [
        [bold(_("node")), bold(_("return code")), bold(_("time"))],
        ROW_SEPARATOR,
    ]

    for node_name, result in sorted(results.items()):
        if result is None:
            continue
        elif result.return_code == 0:
            return_code = green(0)
        else:
            return_code = red(result.return_code)

        stats_table.append([
            node_name,
            return_code,
            format_duration(result.duration),
        ])

    for line in render_table(stats_table):
        io.stdout("{x} {line}".format(x=blue("i"), line=line))
    error_summary(errors)

    exit(1 if errors else 0)
