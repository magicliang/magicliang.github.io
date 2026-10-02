# 第 00 篇实验

从仓库根目录设置 `SCALA_LAB_JAVA_HOME` 为本地 JDK 21，执行：

```sh
python3 examples/scala-lab/run.py chapter 00 --run-id local
```

源码在 `examples/scala-lab/snippets/00/Chapter00.scala` 和共享 `src/main/scala/OrderTotals.scala`。状态：`LAB_VERIFIED`，统一 Scala CLI 与 sbt 入口均 exit=0，包含金额 28.20、空集合 0.00、零数量被拒绝三项断言。正式执行记录在 `examples/scala-lab/evidence/20261002-batch01/all.log`、`sbt.log` 及同名 JSON。
