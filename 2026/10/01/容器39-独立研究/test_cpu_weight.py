import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import cpu_weight as study


class WeightTests(unittest.TestCase):
    def test_counter_delta_and_reject_corruption(self):
        self.assertEqual(study.delta(study.counters("usage_usec 10\nnr_throttled 0\n"),
                                     study.counters("usage_usec 25\nnr_throttled 2\n")),
                         {"usage_usec": 15, "nr_throttled": 2})
        for text in ("user_usec 1", "usage_usec -1", "usage_usec 1\nusage_usec 2", "usage_usec x"):
            with self.assertRaises(ValueError):
                study.counters(text)
        with self.assertRaises(ValueError):
            study.delta({"usage_usec": 20}, {"usage_usec": 10})

    def test_design_has_ten_per_condition_and_reverses_order(self):
        cases = list(study.design(10))
        self.assertEqual(len(cases), 40)
        for name in ("compete", "solo", "solo_high", "swap"):
            self.assertEqual(sum(c["condition"] == name for c in cases), 10)
        self.assertEqual(cases[0]["weights"], {"a": 100, "b": 200})
        self.assertEqual(cases[1]["weights"], {"a": 100})
        self.assertEqual(cases[2]["weights"], {"a": 200})
        self.assertEqual(cases[3]["weights"], {"a": 200, "b": 100})
        self.assertEqual(cases[4]["launch_order"], ["b", "a"])

    def test_rejects_missing_delegation_nonlinux_and_wrong_mount(self):
        with self.assertRaisesRegex(ValueError, "delegated"):
            study.preflight(Path("/unused"), 0, False)
        with patch.object(study.sys, "platform", "darwin"):
            with self.assertRaisesRegex(ValueError, "Linux"):
                study.preflight(Path("/unused"), 0, True)
        with self.assertRaisesRegex(ValueError, "cgroup2"):
            study.cgroup_mount(Path("/sys/fs/cgroup/demo"), "1 2 0:1 / /sys/fs/cgroup rw - cgroup cgroup rw")

    def test_mount_escaping_and_longest_mount(self):
        info = "1 2 0:1 / /a rw - cgroup2 cgroup rw\n2 3 0:1 / /a/b\\040c rw - cgroup2 cgroup rw"
        self.assertEqual(study.cgroup_mount(Path("/a/b c/d"), info), Path("/a/b c"))

    def test_preflight_checks_parent_controller_and_ancestor_quota(self):
        with tempfile.TemporaryDirectory() as folder:
            mount = Path(folder)
            parent = mount / "delegated"
            parent.mkdir()
            for name, value in {"cgroup.subtree_control": "cpu", "cgroup.type": "domain",
                                "cpu.max": "max 100000"}.items():
                (parent / name).write_text(value)
            read_text = Path.read_text

            def read(path, *args, **kwargs):
                if str(path) == "/proc/self/mountinfo":
                    return f"1 2 0:1 / {mount} rw - cgroup2 cgroup rw"
                if str(path).startswith("/proc/"):
                    return "fake test environment"
                return read_text(path, *args, **kwargs)

            with patch.object(study.sys, "platform", "linux"), patch.object(Path, "read_text", read), \
                    patch.object(os, "sched_getaffinity", return_value={0}, create=True), \
                    patch.object(os, "sched_getscheduler", return_value=0, create=True), \
                    patch.object(os, "SCHED_OTHER", 0, create=True):
                self.assertEqual(study.preflight(parent, 0, True)["mount"], str(mount))
                (parent / "cgroup.subtree_control").write_text("")
                with self.assertRaisesRegex(ValueError, "already enable cpu"):
                    study.preflight(parent, 0, True)
                (parent / "cgroup.subtree_control").write_text("cpu")
                (mount / "cpu.max").write_text("10000 100000")
                with self.assertRaisesRegex(ValueError, "ancestor has CPU quota"):
                    study.preflight(parent, 0, True)
                self.assertEqual((parent / "cgroup.subtree_control").read_text(), "cpu")

    def test_worker_migrates_and_sets_affinity_before_ready_and_load(self):
        with tempfile.TemporaryDirectory() as folder:
            group = Path(folder)
            messages, events = [], []
            case = self

            class Channel:
                def send(self, value):
                    messages.append(value)

                def poll(self, timeout):
                    return True

                def recv(self):
                    case.assertTrue(messages[0]["ready"])
                    case.assertEqual((group / "cgroup.procs").read_text(), str(os.getpid()))
                    case.assertEqual(events, [{3}])
                    return time.monotonic() + 0.01

                def close(self):
                    pass

            with patch.object(os, "sched_setaffinity", side_effect=lambda _, cpus: events.append(cpus), create=True), \
                    patch.object(os, "sched_getaffinity", return_value={3}, create=True), \
                    patch.object(study.signal, "signal"):
                study.worker(group, 3, 0.01, Channel())
            self.assertGreater(messages[1]["work_units"], 0)
            self.assertGreaterEqual(messages[1]["actual_start"], messages[1]["scheduled_start"])

    def test_cleanup_only_owned_and_preserves_populated_group(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            empty, busy, other = (root / name for name in ("owned-empty", "owned-busy", "other"))
            for path in (empty, busy, other):
                path.mkdir()
                (path / "cgroup.procs").write_text("123" if path == busy else "")
            rmdir = Path.rmdir

            def fake_cgroup_rmdir(path):
                (path / "cgroup.procs").unlink()
                rmdir(path)

            with patch.object(Path, "rmdir", fake_cgroup_rmdir):
                result = study.cleanup([empty, busy])
            self.assertFalse(result[0]["removed"])
            self.assertTrue(result[1]["removed"])
            self.assertTrue(busy.exists())
            self.assertTrue(other.exists())
            self.assertFalse(empty.exists())

    def check_round(self, fail_ready):
        with tempfile.TemporaryDirectory() as folder:
            groups = {label: Path(folder) / label for label in ("a", "b")}
            for group in groups.values():
                group.mkdir()
                (group / "cpu.stat").write_text("usage_usec 10\n")
            events = []

            class Channel:
                def __init__(self, index):
                    self.index = index
                    self.calls = 0

                def poll(self, timeout):
                    return not fail_ready

                def recv(self):
                    self.calls += 1
                    events.append(("receive", self.index, self.calls))
                    return {"ready": True} if self.calls == 1 else {"work_units": 1}

                def send(self, start):
                    events.append(("send", self.index, start))

                def close(self):
                    pass

            class Process:
                pid = 1
                exitcode = None if fail_ready else 0

                def start(self):
                    pass

                def join(self, timeout):
                    pass

                def is_alive(self):
                    return self.exitcode is None

                def terminate(self):
                    self.exitcode = -15
                    events.append(("terminate",))

            class Context:
                def __init__(self):
                    self.count = 0

                def Pipe(self):
                    self.count += 1
                    channel = Channel(self.count)
                    return channel, channel

                def Process(self, **kwargs):
                    return Process()

            record = {}
            with patch.object(study.mp, "get_context", return_value=Context()):
                if fail_ready:
                    with self.assertRaises(TimeoutError):
                        study.run_round(groups, next(study.design(10)), 0, 0.01, record)
                else:
                    study.run_round(groups, next(study.design(10)), 0, 0.01, record)
            return record, events

    def test_round_broadcasts_same_start_after_both_ready(self):
        record, events = self.check_round(False)
        self.assertEqual(record["status"], "COMPLETED")
        self.assertEqual([e[0] for e in events[:4]], ["receive", "receive", "send", "send"])
        self.assertEqual(events[2][2], events[3][2])
        self.assertEqual(record["workers"]["a"]["exitcode"], 0)

    def test_ready_timeout_terminates_both_workers_without_releasing_load(self):
        record, events = self.check_round(True)
        self.assertEqual(record["status"], "FAILED")
        self.assertEqual(events, [("terminate",), ("terminate",)])
        self.assertEqual(record["workers"]["a"]["exitcode"], -15)
        self.assertEqual(record["workers"]["b"]["exitcode"], -15)

    def test_dry_run_writes_design_without_creating_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            parent, output = Path(folder) / "absent", Path(folder) / "design.json"
            argv = ["cpu_weight.py", "--parent", str(parent), "--cpu", "0", "--output", str(output), "--dry-run"]
            with patch.object(study.sys, "argv", argv):
                self.assertEqual(study.main(), 0)
            result = json.loads(output.read_text())
            self.assertEqual(result["status"], "DESIGN_ONLY_NOT_RUN")
            self.assertEqual(result["rounds"], [])
            self.assertFalse(parent.exists())
            with patch.object(study.sys, "argv", argv), self.assertRaises(FileExistsError):
                study.main()

    def test_rejects_unbounded_duration(self):
        with patch.object(study.sys, "argv", ["cpu_weight.py", "--parent", "/unused", "--cpu", "0",
                                             "--output", "/unused.json", "--seconds", "3"]), \
                patch.object(study.sys, "stderr", io.StringIO()), self.assertRaises(SystemExit):
            study.main()


if __name__ == "__main__":
    unittest.main(verbosity=2)
