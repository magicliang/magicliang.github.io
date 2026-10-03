import unittest
import partition


class MigrationTests(unittest.TestCase):
    def test_actual_collection_is_preserved(self):
        original = {key: f"payload-{key}" for key in range(100)}
        old = partition.place(original, False)
        current = partition.migrate_collection(old)
        partition.verify_collection(current, original)
        self.assertEqual(sum(map(len, current)), 100)
        for number, content in enumerate(current):
            self.assertTrue(all(partition.shard(key, True) == number for key in content))

    def test_missing_copy_is_rejected(self):
        original = {key: f"payload-{key}" for key in range(100)}
        with self.assertRaisesRegex(AssertionError, "missing"):
            partition.verify_collection(partition.migrate_collection(partition.place(original, False), "drop"), original)

    def test_retained_old_copy_is_rejected(self):
        original = {key: f"payload-{key}" for key in range(100)}
        with self.assertRaisesRegex(AssertionError, "duplicate"):
            partition.verify_collection(partition.migrate_collection(partition.place(original, False), "duplicate"), original)


if __name__ == '__main__':
    unittest.main()
