"""Deterministic prefix-index model; no Elasticsearch deployment."""
import json
import platform

words = {'car': 9, 'cart': 7, 'cat': 8, 'dog': 4, 'door': 6}
epoch = 1
cache = {}

def build():
    root, table = {}, {}
    for word in words:
        node = root
        for char in word:
            node = node.setdefault(char, {})
        node['$'] = word
        for length in range(1, len(word) + 1):
            table.setdefault(word[:length], []).append(word)
    for prefix in table:
        table[prefix] = sorted(table[prefix], key=lambda w: (-words[w], w))[:2]
    return root, table

def search(root, prefix):
    node = root
    for char in prefix:
        node = node.get(char, {})
    matches = []
    def walk(part):
        if '$' in part:
            matches.append(part['$'])
        for char, child in part.items():
            if char != '$':
                walk(child)
    walk(node)
    return sorted(matches, key=lambda w: (-words[w], w))[:2]

root, table = build()
queries = ['c', 'ca', 'car', 'd', 'do', 'z']
assert all(search(root, p) == table.get(p, []) for p in queries)
cache[('ca', epoch)] = table['ca'][:]
before = cache[('ca', epoch)]
words['cart'] = 20
words.pop('car')
epoch += 1
root, table = build()
assert before == ['car', 'cat']
assert table['ca'] == ['cart', 'cat']
cache[('ca', epoch)] = before
assert 'car' not in cache[('ca', epoch)]
assert before != table['ca'], 'negative control must expose stale cached result'
print(json.dumps({'python': platform.python_version(), 'queries': len(queries), 'trie_equals_precomputed': True, 'stale_negative': before, 'fresh': table['ca'], 'epoch': epoch, 'pass': True}))
