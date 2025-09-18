from traceback import format_exc

from bundlewrap.concurrency import WorkerPool
from bundlewrap.exceptions import RepositoryError
from bundlewrap.utils.text import red, bold, prefix_lines, _
from bundlewrap.utils.ui import io


def parallel_node_eval(
    nodes,
    expression,
    node_workers,
):
    nodes = set(nodes)

    def tasks_available():
        return bool(nodes)

    def next_task():
        node = nodes.pop()

        def get_values():
            try:
                return eval("lambda node: " + expression)(node)
            except RepositoryError:
                raise
            except Exception:
                traceback = format_exc()
                io.stderr(_(
                    "{x}  {node}  Exception while evaluating `{expression}`, returning as None:\n{traceback}"
                ).format(
                    x=red("✘"),
                    node=bold(node),
                    expression=expression,
                    traceback=prefix_lines("\n" + traceback, f"{red('│')} ") + red("╵"),
                ))
                # Returning None here is kinda meh. But it's the only alternative
                # to failing hard by re-raising, which would be very annoying.
                return None

        return {
            'task_id': node.name,
            'target': get_values,
        }

    def handle_result(task_id, result, duration):
        return task_id, result

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_result=handle_result,
        workers=node_workers,
    )
    return dict(worker_pool.run())
