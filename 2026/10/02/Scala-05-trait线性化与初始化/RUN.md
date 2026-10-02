# Scala 05 实验

状态：`LAB_VERIFIED`。批次 `20261002-batch01` 的 Scala CLI 与 sbt 全章断言均通过，本篇隔离反例均按预期拒绝。

原始证据：`examples/scala-lab/evidence/20261002-batch01/all.log`、`sbt.log` 及各自同名 JSON。本篇拒绝日志为 `negative-05-safe-init.log` 与 `negative-05-trait-argument.log`。JSON 记录具体命令、工作目录与退出码。

冻结环境：Scala CLI 1.9.1、Scala 3.3.7、Amazon Corretto JDK 21.0.11（SDKMAN 安装标识 `21.0.11-amzn`）。

源码位于仓库根目录下的 `examples/scala-lab/snippets/05/Chapter05.scala`，入口为 `scalaexamples.Chapter05.main(Array[String])`。

在仓库根目录执行。先把 `JAVA_HOME` 和 `PATH` 配置为该 JDK，或使用第 00 篇的公共入口：

```bash
python3 examples/scala-lab/run.py chapter 05 --run-id local-05
```

公共入口读取 `SCALA_LAB_JAVA_HOME`。已安装 Scala CLI 1.9.1 时，也可直接运行：

```bash
scala-cli run examples/scala-lab/snippets/05/Chapter05.scala \
  --server=false --scala 3.3.7 --jvm system \
  --main-class scalaexamples.Chapter05
```

验收：退出码 0，所有 assert 通过；标准输出恰含以下程序输出（工具下载提示不属于程序输出）：

```text
first-init=init:Base,init:AddOne,init:DoubleTotal,init:First
first-call=enter:DoubleTotal,enter:AddOne,call:Base,exit:AddOne,exit:DoubleTotal; total=22
second-call=enter:AddOne,enter:DoubleTotal,call:Base,exit:DoubleTotal,exit:AddOne; total=21
trait-argument=arg:Label,init:Label:ready,init:Named
initialization=unsafe:null/ready; safe:ready/ready
```

`UnsafeParent` 故意演示默认模式可观察到的未初始化字段；不要把初始化告警视为默认运行路径必然编译失败。告警拒绝采用独立反例：

```bash
scala-cli compile examples/scala-lab/negative/05/safe-init \
  --server=false --scala 3.3.7 --jvm system \
  --scalac-option -Ysafe-init --scalac-option -Werror
scala-cli compile examples/scala-lab/negative/05/trait-argument \
  --server=false --scala 3.3.7 --jvm system
```

两个反例都应非零退出：前者的诊断必须说明 `name` 未初始化并给出访问链；后者必须说明 trait 不能传入父 trait 构造实参。每个目录的 `case.json` 提供诊断正则与额外选项。不得把下载失败或任意语法错误认作预期拒绝；不得合并目录编译。

安全初始化开关固定为 3.3.7 的 `-Ysafe-init`，`-Werror` 仅负责告警转错误。当前滚动文档的 `-Wsafe-init` 不替换本命令。完整运行日志、退出码与实际环境由公共实验入口记录。
