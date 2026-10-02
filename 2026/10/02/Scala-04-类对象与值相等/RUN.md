# Scala 04 实验说明

状态：LAB_VERIFIED。本章断言已在 Scala CLI 与 sbt 的本批运行中通过，私有访问编译反例也因目标诊断失败。

基线：Scala 3.3.7、Scala CLI 1.9.1、JDK 21（本批冻结发行版 21.0.11-amzn）；无第三方库。完整环境见系列版本表。命令从仓库根目录执行；`--jvm 21` 只表达主版本，精确重跑应选中冻结的本地 JDK。

## 正例与运行时反例

源码：`examples/scala-lab/snippets/04/Chapter04.scala`

入口：`scalaexamples.Chapter04`

```bash
scala-cli run examples/scala-lab/snippets/04/Chapter04.scala --scala 3.3.7 --jvm 21 --server=false --main-class scalaexamples.Chapter04
```

批次运行退出码 0，本章断言全部通过，实测标准输出：

```text
identity=true,false;balances=120,100
valueEqual=true;referenceEqual=false;quantities=2,3
shallowCopy=shared;originalNotes=new,checked
immutableUpdate=2,3
bodyField=ignoredByEquality;copyNote=empty
```

观察覆盖伴生访问、普通类身份、case class 等值与哈希、copy 浅层共享、不可变嵌套更新和类体字段不参与生成相等。共享可变字段是主动断言的运行时反例，整个程序仍应成功。

## 编译反例

```bash
scala-cli compile examples/scala-lab/negative/04/private-access/Example.scala --scala 3.3.7 --jvm 21 --server=false
```

实测退出码 1，诊断包含 `secret cannot be accessed`。失败来自读取私有字段；依赖下载或环境错误不能替代该观察。`case.json` 保存诊断匹配式。

## 实测证据

仓库目录：`examples/scala-lab/evidence/20261002-batch01/`。

- `all.log`、`all.json`：Scala CLI 运行 `scalaexamples.AllChecks`，包含本章五行输出与批次 PASS，退出码 0。
- `sbt.log`、`sbt.json`：sbt 1.11.7 编译并执行 `Test / runMain scalaexamples.AllChecks`，包含本章输出与 success，退出码 0。
- `negative-04-private-access.log` 及同名 JSON：退出码 1，目标私有字段访问诊断。

实际命令选用 Amazon Corretto 21.0.11，并以 `--jvm system` 使用该 JDK；以上独立文件命令是复现入口，完整批次调用与工作目录以 JSON 为准。LAB_VERIFIED 只覆盖已记录的程序与反例，不包含修改练习或页面渲染。
