import pathlib
import tempfile
import unittest
from unittest.mock import patch

import c35_bench


class CgroupLocationTest(unittest.TestCase):
    def snapshot(self, membership, mount_root, relative):
        with tempfile.TemporaryDirectory(prefix="c35 ") as temporary:
            mount = pathlib.Path(temporary)
            own = mount / relative
            own.mkdir(parents=True, exist_ok=True)
            (mount / "cpu.max").write_text("max 100000\n")
            (own / "cpu.max").write_text("10000 100000\n")
            (own / "cpu.stat").write_text("nr_throttled 7\n")
            escaped = str(mount).replace(" ", r"\040")
            mountinfo = f"42 1 0:29 {mount_root} {escaped} rw - cgroup2 cgroup rw\n"
            real_read = pathlib.Path.read_text

            def read(path, *args, **kwargs):
                if str(path) == "/proc/self/cgroup":
                    return f"0::{membership}\n"
                if str(path) == "/proc/self/mountinfo":
                    return "1 0 0:1 / / rw - tmpfs tmpfs rw\n" + mountinfo
                return real_read(path, *args, **kwargs)

            with patch.object(pathlib.Path, "read_text", read), patch.object(
                    c35_bench.os, "sched_getaffinity", return_value={0}, create=True):
                result = c35_bench.environment()
            self.assertEqual(result["controllers"]["cpu.max"], "10000 100000\n")
            self.assertEqual(result["controllers"]["cpu.stat"], "nr_throttled 7\n")
            self.assertIsNone(result["controllers"]["memory.max"])
            self.assertEqual(result["cgroup_source"]["directory"], str(own))
            self.assertEqual(result["cgroup_source"]["mount_root"], mount_root)
            self.assertEqual(result["cgroup_source"]["membership"], membership)
            self.assertEqual(result["cgroup_source"]["mountinfo_line"], mountinfo.strip())

    def test_nested_host_group(self):
        self.snapshot("/user.slice/session.scope", "/", "user.slice/session.scope")

    def test_subtree_mount(self):
        self.snapshot("/user.slice/session.scope", "/user.slice", "session.scope")

    def test_namespace_root(self):
        self.snapshot("/", "/", "")

    def test_namespace_child(self):
        self.snapshot("/worker", "/", "worker")

    def test_unresolvable_mount_does_not_fall_back_to_root(self):
        with self.assertRaisesRegex(ValueError, "cannot map"):
            c35_bench.cgroup_location("0::/worker\n", "42 1 0:29 /other /tmp rw - cgroup2 cgroup rw")
        with self.assertRaisesRegex(ValueError, "cannot map"):
            c35_bench.cgroup_location("0::/\n", "42 1 0:29 /.. /tmp rw - cgroup2 cgroup rw")

    def test_v1_and_outside_namespace_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "cgroup v2"):
            c35_bench.cgroup_location("1:cpu:/worker\n", "")
        with self.assertRaisesRegex(ValueError, "outside"):
            c35_bench.cgroup_location("0::/../worker\n", "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
