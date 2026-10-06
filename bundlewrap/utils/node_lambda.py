from bundlewrap.concurrency import WorkerPool


def parallel_node_eval(
    nodes,
    expression,
    workers,
):
    nodes = set(nodes)

    def tasks_available():
        return bool(nodes)

    def next_task():
        node = nodes.pop()

        def get_values():
            return eval("lambda node: " + expression)(node)

        return {
            'task_id': node.name,
            'target': get_values,
        }

    def handle_result(task_id, result, _duration):
        return task_id, result

    worker_pool = WorkerPool(
        tasks_available,
        next_task,
        handle_result=handle_result,
        workers=workers,
    )
    return dict(worker_pool.run())
