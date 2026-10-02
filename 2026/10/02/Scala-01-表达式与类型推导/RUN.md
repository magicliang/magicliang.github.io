# 第 01 篇实验

在仓库根目录设置本地 JDK 21 后执行 `python3 examples/scala-lab/run.py chapter 01 --run-id local`。反例用 `negative` 模式统一执行。

正例：`snippets/01/Chapter01.scala`。反例：`negative/01/block-unit/`、`negative/01/widening/`。源码路径均相对 `examples/scala-lab/`。状态：`LAB_VERIFIED`。Scala CLI 与 sbt 统一入口均 exit=0，结果为 amount=28.20、fee=4.00、mixed=pending、precedence=14/20。两个反例均 exit=1 且命中目标诊断。实际记录位于 `examples/scala-lab/evidence/20261002-batch01/all.log`、`sbt.log`、`negative-01-block-unit.log`、`negative-01-widening.log` 及同名 JSON。
