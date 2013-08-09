from datetime import datetime

from ..concurrency import WorkerPool
from ..utils import LOG
from ..utils.cmdline import get_target_nodes
from ..utils.text import mark_for_translation as _


def _format_output(nodename, stream, msg):
    # remove "[host] out: " prefix from Fabric
    needle = ": "
    msg = msg[msg.find(needle) + len(needle):]
    return "{} ({}): {}".format(nodename, stream, msg)


def run_on_node(node, command, may_fail, sudo, verbose):
    start = datetime.now()
    result = node.run(
        command,
        may_fail=may_fail,
        stderr=lambda msg: LOG.warn(_format_output(node.name, "stderr", msg)),
        stdout=lambda msg: LOG.info(_format_output(node.name, "stdout", msg)),
        sudo=sudo,
    )
    end = datetime.now()
    duration = end - start
    if result.return_code == 0:
        yield _("{}: completed successfully after {}s").format(
            node.name,
            duration.total_seconds(),
        )
    else:
        if not verbose:
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


def bw_run(repo, args):
    target_nodes = get_target_nodes(repo, args.target)
    with WorkerPool(workers=args.node_workers) as worker_pool:
        while (
                target_nodes or
                worker_pool.busy_count > 0 or
                worker_pool.reapable_count > 0
        ):
            while target_nodes:
                worker = worker_pool.get_idle_worker(block=False)
                if worker is None:
                    break
                node = target_nodes.pop()

                worker.start_task(
                    run_on_node,
                    id=node.name,
                    args=(
                        node,
                        args.command,
                        args.may_fail,
                        args.sudo,
                        args.verbose,
                    ),
                )
            while worker_pool.reapable_count > 0:
                worker = worker_pool.get_reapable_worker()
                for line in worker.reap():
                    yield line
            if (
                worker_pool.busy_count > 0 and
                not target_nodes and
                not worker_pool.reapable_count
            ):
                worker_pool.wait()
