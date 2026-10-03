# 第 21 篇实验

LAB_VERIFIED；Scala 3.3.7 / stdlib 2.13.16 / JDK 21.0.11-amzn / Scala CLI 1.9.1。

从仓库根目录执行：

```bash
export SCALA_LAB_JAVA_HOME=/Users/magicliang/.sdkman/candidates/java/21.0.11-amzn
export SCALA_LAB_CLI_JAR=/private/tmp/scala-lab-cli-1.9.1.jar
python3 examples/scala-lab/run.py chapter 21 --run-id 20261002-ch21-r3
python3 examples/scala-lab/run.py negative 21 --run-id 20261002-ch21-r3
```

源码：examples/scala-lab/snippets/21/Chapter21.scala；入口 scalaexamples.Chapter21。

正例实际 exit=0，输出：

```text
constructed=1;evaluated=0->2->4;context=100,200;captured=100;later=200
```

隔离反例 negative/21/missing-context 实际 exit=1，并匹配 case.json 的全部诊断正则。完整命令、退出码与输出位于 examples/scala-lab/evidence/20261002-ch21-r3/21.json、21.log、negative-21-missing-context.json 和对应 .log；environment.txt 保存工具版本。

普通 build 工厂内记录构造次数，make 计算体内记录执行次数。最终版本采用普通 final class 保存上下文函数。 本章不包含全站页面或全工程集成验收。
