# 第 18 篇实验

LAB_VERIFIED；Scala 3.3.7 / stdlib 2.13.16 / JDK 21.0.11-amzn / CLI 1.9.1。

```bash
export SCALA_LAB_JAVA_HOME=/Users/magicliang/.sdkman/candidates/java/21.0.11-amzn
export SCALA_LAB_CLI_JAR=/private/tmp/scala-lab-cli-1.9.1.jar
python3 examples/scala-lab/run.py chapter 18 --run-id 20261002-ch18
python3 examples/scala-lab/run.py negative 18 --run-id 20261002-ch18
```

源码 snippets/18/Chapter18.scala，入口 scalaexamples.Chapter18；实际正例 exit=0，各反例 exit=1 且每条 manifest 诊断匹配。证据 examples/scala-lab/evidence/20261002-ch18/18.log/.json，negative-18-*.log/.json 和 environment.txt。

16 另有 javap.log：命令、exit=0、lookup(long)及(J)J描述符；运行时对象边界看到 java.lang.Long，不宣称所有路径零分配。17 的同名 label 警告是有意的成员优先对照，显式扩展调用仍得到另一结果，实际警告保留在日志。18 未执行 Scala 2 迁移对照，不把 Scala 3 搜索结论套到 Scala 2。集成构建与页面由 root 验证。

