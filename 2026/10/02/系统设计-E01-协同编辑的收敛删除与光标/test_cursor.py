import unittest
from itertools import permutations
import run as model


class CursorTests(unittest.TestCase):
    def test_deleted_parent_resolves_before_child_in_every_order(self):
        for order in permutations(model.ops):
            self.assertEqual(model.resolve_cursor(order, 'a1', 'after'), 0)
            visible, _ = model.merge(order)
            self.assertEqual(visible[0][0], 'a2')

    def test_unrelated_prefix_changes_offset_not_anchor(self):
        order = model.ops + [('i', '00', 'ROOT', 'Y')]
        self.assertEqual(model.resolve_cursor(order, 'a1', 'after'), 1)
        self.assertEqual(model.merge(order)[0][1][0], 'a2')

    def test_deleted_leaf_and_end(self):
        self.assertEqual(model.resolve_cursor(model.ops, 'b1', 'after'), 2)
        self.assertEqual(model.resolve_cursor(model.ops + [('d', 'b1')], 'b1', 'after'), 1)
        self.assertEqual(model.resolve_cursor(model.ops, 'a1', 'before'), 0)
        self.assertEqual(model.resolve_cursor(model.ops, 'ROOT', 'after'), 0)

    def test_unknown_anchor_and_invalid_affinity_rejected(self):
        with self.assertRaises(ValueError):
            model.resolve_cursor(model.ops, 'missing', 'after')
        with self.assertRaises(ValueError):
            model.resolve_cursor(model.ops, 'a1', 'leftish')


if __name__ == '__main__':
    unittest.main()
