# Scala 03 实验说明

状态：LAB_VERIFIED。本章断言已在 Scala CLI 与 sbt 的本批运行中通过，两项编译反例也因目标诊断失败。

基线：Scala 3.3.7、Scala CLI 1.9.1、JDK 21（本批冻结发行版 21.0.11-amzn）；无第三方库。完整环境见系列版本表。命令从仓库根目录执行；`--jvm 21` 只表达主版本，精确重跑应选中冻结的本地 JDK。

## 正例与运行时反例

源码：`examples/scala-lab/snippets/03/Chapter03.scala`

入口：`scalaexamples.Chapter03`

```bash
scala-cli run examples/scala-lab/snippets/03/Chapter03.scala --scala 3.3.7 --jvm 21 --server=false --main-class scalaexamples.Chapter03
```

批次运行退出码 0，本章断言全部通过，实测标准输出：

```text
pricing=180,160,180
capture=180,160,180
partial=Some(2),None;collect=1,2;undefined=MatchError
firstPositive=Some(7),None
```

四组观察分别覆盖方法转换/偏应用、可变捕获与值快照、PartialFunction 定义域/collect/lift/运行时 MatchError、显式 Option 查找结果。

## 编译反例

```bash
scala-cli compile examples/scala-lab/negative/03/function-is-not-partial/Example.scala --scala 3.3.7 --jvm 21 --server=false
scala-cli compile examples/scala-lab/negative/03/nonlocal-return/Example.scala --scala 3.3.7 --jvm 21 --server=false --scalac-option -Werror
```

两条编译反例实测退出码均为 1。第一条诊断包含 `isDefinedAt is not a member`；第二条包含 `Non local returns are no longer supported`。第二条是在 `-Werror` 策略下把非局部返回警告升级为失败，不能解释成所有 `return` 均已被语言删除。各目录的 `case.json` 存储诊断匹配式。

## 实测证据

仓库目录：`examples/scala-lab/evidence/20261002-batch01/`。

- `all.log`、`all.json`：Scala CLI 运行 `scalaexamples.AllChecks`，包含本章四行输出与批次 PASS，退出码 0。
- `sbt.log`、`sbt.json`：sbt 1.11.7 编译并执行 `Test / runMain scalaexamples.AllChecks`，包含本章输出与 success，退出码 0。
- `negative-03-function-is-not-partial.log` 及同名 JSON：退出码 1，目标成员不存在诊断。
- `negative-03-nonlocal-return.log` 及同名 JSON：退出码 1，命令含 `-Werror`，非局部返回警告提升为失败。

实际命令选用 Amazon Corretto 21.0.11，并以 `--jvm system` 使用该 JDK；以上独立文件命令是复现入口，完整批次调用与工作目录以 JSON 为准。依赖下载、JDK 或命令不可用属于环境失败，不能算反例通过。LAB_VERIFIED 只覆盖已记录的程序与反例，不包含修改练习或页面渲染。
