# 06 VM 补跑入口

材料：源码包 `bounded_load.py`，仅标准库；先在**专用 Linux VM** 确认 `stat -fc %T /sys/fs/cgroup` 是 `cgroup2fs`，并由管理员给当前用户委派一个私有可写的子树。当前云端 cgroup v1 只读，所有下述限制/竞争实验 `NOT_RUN`。请先保存 `/proc/self/cgroup` 和 `cat /sys/fs/cgroup/cgroup.controllers`，不写宿主根 cgroup。

```sh
python3 bounded_load.py --seconds 1 --memory-mib 0
cat "$DELEGATED_CGROUP/cpu.max" "$DELEGATED_CGROUP/cpu.weight" "$DELEGATED_CGROUP/cpuset.cpus.effective"
cat "$DELEGATED_CGROUP/cpu.stat"
```

在自己拥有的子组内分别设 `cpu.max=50000 100000`、对照默认值，并用两个同样有界负载制造竞争；前后保存 `cpu.stat`，最多运行 2 秒/轮。预期硬配额可有节流增量，只有竞争时 weight 差异才有解释力；实际尚无计数器输出。最后停止自己的进程、检查子组 `cgroup.procs` 为空并删除自己创建的子组。不要在共享环境中执行配置/压力操作。
