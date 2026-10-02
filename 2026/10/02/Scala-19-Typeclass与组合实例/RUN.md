# 第 19 篇实验

LAB_VERIFIED；Scala 3.3.7 / stdlib 2.13.16 / JDK 21.0.11-amzn / Scala CLI 1.9.1。

从仓库根目录执行：

```bash
export SCALA_LAB_JAVA_HOME=/Users/magicliang/.sdkman/candidates/java/21.0.11-amzn
export SCALA_LAB_CLI_JAR=/private/tmp/scala-lab-cli-1.9.1.jar
python3 examples/scala-lab/run.py chapter 19 --run-id 20261002-ch19
python3 examples/scala-lab/run.py negative 19 --run-id 20261002-ch19
```

源码：examples/scala-lab/snippets/19/Chapter19.scala；入口 scalaexamples.Chapter19。

正例实际 exit=0，输出：

```text
nested=[[1,2],[]];compact=order:7;verbose=Order(id=7);composed=[order:7]
```

隔离反例 negative/19/missing-instance 实际 exit=1，并匹配 case.json 的全部诊断正则。完整命令、退出码与输出位于 examples/scala-lab/evidence/20261002-ch19/19.json、19.log、negative-19-missing-instance.json 和对应 .log；environment.txt 保存工具版本。

两种业务编码策略均显式选取；组合实例只检查本文的嵌套输入，未声称能终止任意递归搜索。 本章不包含全站页面或全工程集成验收。

