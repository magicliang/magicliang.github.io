# 07 VM 补跑入口

仅专用 Linux VM、cgroup v2、管理员已委派的子组。运行探针前获取 `memory.max`、`memory.events`、`pids.max`、`io.max` 的初值与设备号。下面负载自身最多申请 32 MiB、运行两秒；不做无界内存申请或大规模 fork。

```sh
cat "$DELEGATED_CGROUP/memory.events" "$DELEGATED_CGROUP/pids.events" "$DELEGATED_CGROUP/io.stat"
python3 bounded_load.py --memory-mib 8 --seconds 1
cat "$DELEGATED_CGROUP/memory.events" "$DELEGATED_CGROUP/pids.events" "$DELEGATED_CGROUP/io.stat"
```

独立 pids 补充附件：先在本目录执行 `sha256sum -c PIDS_CHECKSUMS.sha256`，用本目录的 `pids_probe.py`（共用代码原本在 `examples/containers/pids_probe.py`）在 VM 的委派组内运行 `python3 pids_probe.py --children 2 --hold-seconds 0.1`，固定最多 4 个自建子进程、每个最多等待 2 秒；保留 `pids.current`/`pids.events` 前后和每次创建结果。普通无 pids 限制的本机正常分支见 `pids-normal-raw.txt`，只说明创建并回收两个子进程成功；拒绝分支 `NOT_RUN`。若需控制器拒绝，在专用 VM 的**委派组**由管理员设不高于当前任务数的 `pids.max`，先记录组里原有任务，不能给共享宿主或其他任务的组限额。

限制组内做对照需要保存配置和预期、程序真实退出码及计数增量。要测试内存限制先确保 Python 基础用量加分配额不超过专用 VM 的安全预算；I/O 需锁定设备及缓存条件；PIDs 只允许少量自建子进程。停止全部自己创建的子进程，确认组为空后复原自身子组并清理；共享云端 cgroup v1 只读，本篇所有 **v2 控制器** 实验仍 `NOT_RUN`。
