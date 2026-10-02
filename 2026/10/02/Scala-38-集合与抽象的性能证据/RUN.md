# Scala 38 重跑

在仓库根目录执行，JAVA_HOME 指向 JDK 21；工具缓存放临时目录，不提交 jar/class。

```bash
export SCALA_LAB_JAVA_HOME="$JAVA_HOME"
python3 examples/scala-lab/run.py chapter 38 --run-id local-ch38-correctness
python3 examples/scala-lab/modules/38/run.py prepare --run-id local-ch38
python3 examples/scala-lab/modules/38/run.py timing --run-id local-ch38
python3 examples/scala-lab/modules/38/run.py gc --run-id local-ch38
```

冻结：Scala 3.3.7、Scala CLI 1.9.1、JMH 1.37、Corretto JDK 21.0.11。prepare 编译 Scala 工作负载、运行正确性断言、用 Java annotation processor 生成 JMH 入口、列出基准，并输出实际 javap 字节码。

timing：1线程，2fork，每fork预热2×1s、测量3×1s，512/4096行，256MiB固定堆，无profiler。gc：另开1fork，预热1×500ms、测量1×500ms，512行，GC profiler。两个运行的时间数值不得混用。

实测记录：`examples/scala-lab/modules/38/evidence/20261002-ch38/`。`timing-results.json` 的8组结果各保存2×3原始样本；`gc-results.json` 的4组结果包含 `gc.alloc.rate.norm`。同名日志和命令JSON，以及依赖摘要、JDK和机器记录随源码保留。新增产物证据在 `evidence/20261002-ch38-artifacts/`，其中 bytecode.log/json 保留javap的真实输出和命令；工作负载与测量时相同，没有重测并替换原始性能数值。

原始 `machine.json` 是GC阶段的机器/负载快照；当前runner按phase分别生成 `prepare-machine.json`、`timing-machine.json`、`gc-machine.json`。本机是共享主机，其他编译任务同时运行；计时只作实验观测，不支持全局性能排序、生产吞吐或尾延迟结论。
