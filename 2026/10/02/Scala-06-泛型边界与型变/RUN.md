# Scala 06 实验

状态：`LAB_VERIFIED`。批次 `20261002-batch01` 的 Scala CLI 与 sbt 全章断言均通过，本篇隔离反例均按预期拒绝。

原始证据：`examples/scala-lab/evidence/20261002-batch01/all.log`、`sbt.log` 及各自同名 JSON。本篇拒绝日志为 `negative-06-covariant-var.log`、`negative-06-invariant-assignment.log`、`negative-06-function-direction.log`、`negative-06-upper-bound.log`、`negative-06-covariant-input.log`。JSON 记录具体命令、工作目录与退出码。

冻结环境：Scala CLI 1.9.1、Scala 3.3.7、Amazon Corretto JDK 21.0.11（SDKMAN 安装标识 `21.0.11-amzn`）。

源码位于仓库根目录下的 `examples/scala-lab/snippets/06/Chapter06.scala`，入口为 `scalaexamples.Chapter06.main(Array[String])`。

在仓库根目录执行。先把 `JAVA_HOME` 和 `PATH` 配置为该 JDK，或使用第 00 篇的公共入口：

```bash
python3 examples/scala-lab/run.py chapter 06 --run-id local-06
```

公共入口读取 `SCALA_LAB_JAVA_HOME`。已安装 Scala CLI 1.9.1 时，也可直接运行：

```bash
scala-cli run examples/scala-lab/snippets/06/Chapter06.scala \
  --server=false --scala 3.3.7 --jvm system \
  --main-class scalaexamples.Chapter06
```

验收：退出码 0，assert 全部通过，程序输出如下：

```text
variance=Source[Create]->Source[Command]; Sink[Command]->Sink[Create]
function=o-1
bounds=o-2,o-1; original=1
mutable-element=paid; same-reference=true
```

反例单独编译，按需要替换最后一级目录：

```bash
scala-cli compile examples/scala-lab/negative/06/covariant-var \
  --server=false --scala 3.3.7 --jvm system
```

| 最后一级目录 | 预期失败语义 |
| --- | --- |
| `covariant-var` | 协变类型 A 出现在公开赋值参数的逆变位置 |
| `invariant-assignment` | Cell[Create] 不满足 Cell[Command] |
| `function-direction` | Create => Command 不满足 Command => Create |
| `upper-bound` | 显式类型参数 String 不满足 Command 上界 |
| `covariant-input` | 协变 A 不能直接出现在 prepend 的输入参数 |

每个反例目录的 `case.json` 提供预期诊断正则。全部反例都要求非零退出并匹配每一项诊断模式；依赖下载失败、语法拼写错误和其他目录的错误不能代替预期语义。不要一次编译全部 `negative/06`。

无强制转换、外部服务或随机输入。完整运行日志、退出码与实际环境由公共实验入口记录。
