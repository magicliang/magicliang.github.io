# 第 20 篇实验

LAB_VERIFIED；Scala 3.3.7 / stdlib 2.13.16 / JDK 21.0.11-amzn / Scala CLI 1.9.1。

从仓库根目录执行：

```bash
export SCALA_LAB_JAVA_HOME=/Users/magicliang/.sdkman/candidates/java/21.0.11-amzn
export SCALA_LAB_CLI_JAR=/private/tmp/scala-lab-cli-1.9.1.jar
python3 examples/scala-lab/run.py chapter 20 --run-id 20261002-ch20
python3 examples/scala-lab/run.py negative 20 --run-id 20261002-ch20
```

源码：examples/scala-lab/snippets/20/Chapter20.scala；入口 scalaexamples.Chapter20。

正例实际 exit=0，输出：

```text
laws=4-inputs,5-laws;either=Right(200),Left(quantity);brokenFunctor=detected
```

隔离反例 negative/20/wrong-kind 实际 exit=1，并匹配 case.json 的全部诊断正则。完整命令、退出码与输出位于 examples/scala-lab/evidence/20261002-ch20/20.json、20.log、negative-20-wrong-kind.json 和对应 .log；environment.txt 保存工具版本。

四个输入上的五项断言用于发现实现错误，不构成对所有值的定律证明；故意破坏 identity 的实例确实被对照断言识别。 本章不包含全站页面或全工程集成验收。

