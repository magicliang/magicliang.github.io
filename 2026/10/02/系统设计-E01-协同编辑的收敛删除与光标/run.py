import itertools
import json
import platform

ops = [('i', 'a1', 'ROOT', 'A'), ('i', 'b1', 'ROOT', 'B'),
       ('i', 'a2', 'a1', 'x'), ('d', 'a1')]


def layout(order):
    nodes, deleted = {}, set()
    for op in order:
        if op[0] == 'i':
            _, key, parent, text = op
            if key in nodes:
                assert nodes[key] == (parent, text)
            nodes[key] = (parent, text)
        else:
            deleted.add(op[1])

    def walk(parent):
        result = []
        for key in sorted(key for key, value in nodes.items() if value[0] == parent):
            result.append((key, nodes[key][1]))
            result.extend(walk(key))
        return result
    return walk('ROOT'), deleted


def merge(order):
    ordered, deleted = layout(order)
    return [entry for entry in ordered if entry[0] not in deleted], deleted


def resolve_cursor(order, anchor, affinity):
    if affinity not in ('before', 'after'):
        raise ValueError('affinity must be before or after')
    ordered, deleted = layout(order)
    if anchor == 'ROOT':
        return 0
    keys = [key for key, _ in ordered]
    if anchor not in keys:
        raise ValueError('unknown anchor')
    boundary = keys.index(anchor) + (affinity == 'after')
    return sum(key not in deleted for key in keys[:boundary])


def run():
    results = {''.join(ch for _, ch in merge(order)[0])
               for order in itertools.permutations(ops)}
    assert results == {'xB'}
    assert merge(ops + ops) == merge(ops)
    visible, _ = merge(ops)
    cursor = resolve_cursor(ops, 'a1', 'after')
    assert visible[cursor][0] == 'a2'
    prefixed = ops + [('i', '00', 'ROOT', 'Y')]
    prefixed_cursor = resolve_cursor(prefixed, 'a1', 'after')
    assert prefixed_cursor == 1 and merge(prefixed)[0][prefixed_cursor][0] == 'a2'
    end_cursor = resolve_cursor(ops, 'b1', 'after')
    assert end_cursor == len(visible)

    def positional(order):
        text = ''
        for ch in order:
            text = ch + text
        return text
    assert positional('AB') != positional('BA')
    print(json.dumps(dict(
        python=platform.python_version(), permutations=24, converged=sorted(results),
        duplicate_idempotent=True, cursor_after_deleted_a1='before ' + visible[cursor][0],
        cursor_offset=cursor, prefixed_cursor_offset=prefixed_cursor,
        end_cursor_offset=end_cursor, negative_offsets=[positional('AB'), positional('BA')],
        pass_checks=True), indent=2))


if __name__ == '__main__':
    run()
