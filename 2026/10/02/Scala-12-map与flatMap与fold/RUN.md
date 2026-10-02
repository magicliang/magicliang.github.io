# 第 12 篇实验

状态 LAB_VERIFIED；Scala 3.3.7 / stdlib 2.13.16 / JDK 21.0.11-amzn / CLI 1.9.1。

源码 examples/scala-lab/snippets/12/Chapter12.scala，入口 scalaexamples.Chapter12。

```bash
export SCALA_LAB_JAVA_HOME=/Users/magicliang/.sdkman/candidates/java/21.0.11-amzn
export SCALA_LAB_CLI_JAR=/private/tmp/scala-lab-cli-1.9.1.jar
python3 examples/scala-lab/run.py chapter 12 --run-id 20261002-ch12
python3 examples/scala-lab/run.py negative 12 --run-id 20261002-ch12
```

实际正例退出 0；隔离反例退出 1 且 case.json 的每条诊断表达式匹配。完整输出、命令及环境在 examples/scala-lab/evidence/20261002-ch12/。正常日志 12.log；反例日志以 negative-12- 开头。11 只验证计算次数、对象身份和保留头引用的可重访性，没有测量堆占用或 GC 回收。10 没有微基准，12 循环等价断言不代替性能测试。整批构建和页面验证由 root 集成。

