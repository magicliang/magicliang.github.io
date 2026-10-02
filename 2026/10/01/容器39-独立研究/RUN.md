# 39 CPU weight 可证伪实验

下载同目录 [cpu_weight.py](cpu_weight.py) 和 [test_cpu_weight.py](test_cpu_weight.py)。脚本仅用 Python 标准库，内置相同整数运算负载并记录脚本 SHA256；旧附件中的 `bounded_load.py` 不承担本实验调度。

## 运行

在专用 Linux VM 中，由管理员提前提供已委派给当前用户、可创建子组且 `cgroup.subtree_control` 已含 `cpu` 的父目录。将命令中的目录与 CPU 编号替换为真实值；脚本不创建这个父目录、不启用其 controller。父组到可见挂载根的 `cpu.max` 必须均无限额；隐藏祖先无法检查，仍需宿主记录。固定内核、CPU 拓扑/频率、cpuset 与其他负载后运行。

```sh
python3 cpu_weight.py --parent /sys/fs/cgroup/your-delegated-group --delegated --cpu 0 --output weight-run.json
```

每种条件默认重复十次，共四十轮：A:B 为 100:200 竞争、仅 A=100 运行、仅 A=200 运行、交换为 200:100 竞争。偶数轮反转条件及进程创建顺序。两负载先迁移到新建子组、固定在同一个 CPU，全部就绪后才接收相同起跑时刻；每轮工作窗口最多两秒，记录实际起止时间与调度延迟，不把同步释放当作零启动偏差。JSON 保存每轮权重、`cpu.stat` 原文前后及差分、工作次数、时间、退出码、已尝试轮次失败率与清理结果。`cpu.stat` 差分还包含就绪后等待起跑和退出的少量开销；负载自身的 CPU 时间另列 `process_cpu_seconds`。观察完成不自动判定 weight 比例成立。

## 本机设计检查

```sh
python3 cpu_weight.py --parent /sys/fs/cgroup/your-delegated-group --cpu 0 --dry-run --output weight-design.json
python3 test_cpu_weight.py
```

`--dry-run` 只写设计 JSON，状态为 `DESIGN_ONLY_NOT_RUN`，不校验 Linux 环境、不创建 cgroup、不运行负载；测试使用临时普通目录与模拟接口，不能证明内核调度结果。真实基线、十次重复、反例及恢复观测仍为 `NOT_RUN`，须在合格 VM 运行后据实更新。脚本只删除自己随机命名目录下创建的空组；异常时终止自己启动的子进程，保留失败 JSON，清理失败返回非零退出码。输出文件必须不存在，以免覆盖旧证据；SIGKILL、断电无法执行进程内清理，需核实 `weight-study-*` 目录归属后恢复。可见祖先不限额也不等于没有同机干扰，应结合 `start_lateness_seconds`、节流差分及宿主负载解释异常；两秒是工作截止窗口，调度延迟、准备和收集时间另计。

原始来源：[Linux kernel cgroup v2 CPU controller](https://docs.kernel.org/admin-guide/cgroup-v2.html#cpu)（核查日期：2026-10-01）。`cpu.weight` 按活跃竞争组分配 CPU，`cpu.stat` 时间计数单位为微秒，`cpu.max=max` 表示该层不设带宽上限；进程通过写 `cgroup.procs` 迁移，空组通过 `rmdir` 删除。
