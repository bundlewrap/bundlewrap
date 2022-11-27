from os import environ
from sys import exit
from traceback import format_exc

from ..concurrency import WorkerPool
from ..exceptions import RepositoryError
from ..node import NODE_ATTRS
from ..utils.cmdline import get_target_nodes
from ..utils.table import ROW_SEPARATOR, render_table
from ..utils.text import bold, green, mark_for_translation as _, prefix_lines, red, yellow
from ..utils.ui import io, page_lines


def attrs_for_entities(
    entities,
    selected_attrs,
    node_workers,
):
    entities = entities.copy()

    def tasks_available():
        return bool(entities)

    def next_task():
        entity = entities.pop()

        def get_values():
            result = {}
            for attr in selected_attrs:
                try:
                    result[attr] = getattr(entity, attr)
                except RepositoryError:
                    raise
                except Exception as exc:
                    traceback = format_exc()
                    io.stderr(_(
                        "{x}  {entity}  Exception while getting '{attr}':\n{traceback}"
                    ).format(
                        x=red("✘"),
                        entity=bold(entity),
                        attr=attr,
                        traceback=prefix_lines("\n" + traceback, f"{red('│')} ") + red("╵"),
                    ))
                    result[attr] = red(exc.__class__.__name__)
            return result

        return {
            'task_id': entity.name,
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


def attribute_table(
    results,
    entity_label,
    selected_attrs,
    available_attrs,
    inline,
):
    rows = [[entity_label], ROW_SEPARATOR]

    for attr in selected_attrs:
        rows[0].append(bold(attr))

    has_list_attrs = False
    for entity_name, values in sorted(results.items()):
        attr_values = [[entity_name]]
        for attr in selected_attrs:
            value = values[attr]
            if value is True:
                attr_values.append([green("True")])
            elif value is False:
                attr_values.append([red("False")])
            elif value is None:
                attr_values.append([yellow("None")])
            elif isinstance(value, set):
                if inline or environ.get("BW_TABLE_STYLE") == 'csv':
                    attr_values.append([",".join([str(v) for v in sorted(value)])])
                else:
                    has_list_attrs = True
                    attr_values.append([str(v) for v in sorted(value)])
            elif isinstance(value, (list, tuple)):
                if inline or environ.get("BW_TABLE_STYLE") == 'csv':
                    attr_values.append([",".join([str(v) for v in value])])
                else:
                    has_list_attrs = True
                    attr_values.append([str(v) for v in value])
            else:
                attr_values.append([str(value)])
        number_of_lines = max([len(value) for value in attr_values])
        if environ.get("BW_TABLE_STYLE") == 'grep':
            # repeat entity name for each line
            attr_values[0] = attr_values[0] * number_of_lines
        for line in range(number_of_lines):
            row = []
            for attr_index in range(len(selected_attrs) + 1):
                try:
                    row.append(attr_values[attr_index][line])
                except IndexError:
                    row.append("")
            rows.append(row)
        if has_list_attrs:
            rows.append(ROW_SEPARATOR)
    if environ.get("BW_TABLE_STYLE") == 'grep':
        rows = rows[2:]
    page_lines(render_table(
        rows[:-1] if has_list_attrs else rows,  # remove trailing ROW_SEPARATOR
    ))


def select_attrs(selected_attrs, available_attrs):
    selected_attrs = [attr.strip() for attr in selected_attrs]

    if selected_attrs == ['all']:
        selected_attrs = available_attrs
    elif 'all' in selected_attrs:
        io.stderr(_(
            "{x} invalid attribute list requested ('all' and extraneous): {attr}"
        ).format(x=red("!!!"), attr=", ".join(sorted(selected_attrs))))
        exit(1)

    for attr in selected_attrs:
        if attr not in available_attrs:
            io.stderr(_("{x} unknown attribute: {attr}").format(x=red("!!!"), attr=attr))
            exit(1)

    return selected_attrs, available_attrs


def bw_nodes(repo, args):
    if args['targets']:
        nodes = get_target_nodes(repo, args['targets'], args['node_workers'])
    else:
        nodes = repo.nodes
    if not args['attrs']:
        for node in sorted(nodes):
            io.stdout(node.name)
    else:
        selected_attrs, available_attrs = select_attrs(
            args['attrs'],
            NODE_ATTRS + list(repo.node_attribute_functions.keys()),
        )
        results = attrs_for_entities(
            nodes,
            selected_attrs,
            args['node_workers'],
        )
        attribute_table(
            results,
            bold(_("node")),
            selected_attrs,
            available_attrs,
            args['inline'],
        )
