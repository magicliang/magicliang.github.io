# 第 14 篇实验

LAB_VERIFIED：Scala 3.3.7 / stdlib 2.13.16 / JDK 21.0.11-amzn / CLI 1.9.1。

源码 examples/scala-lab/snippets/14/Chapter14.scala；入口 scalaexamples.Chapter14。

```bash
export SCALA_LAB_JAVA_HOME=/Users/magicliang/.sdkman/candidates/java/21.0.11-amzn
export SCALA_LAB_CLI_JAR=/private/tmp/scala-lab-cli-1.9.1.jar
python3 examples/scala-lab/run.py chapter 14 --run-id 20261002-ch14
python3 examples/scala-lab/run.py negative 14 --run-id 20261002-ch14
```

正例实际 exit=0；全部本章反例实际 exit=1，case.json 每条目标诊断匹配。证据 examples/scala-lab/evidence/20261002-ch14/ 下的 14.log/.json、negative-14-*.log/.json 及 environment.txt。13 的 refutable-pattern 用 -Werror 提升警告；Either 守卫缺 withFilter 是类型错误。14 验证十万项运行与注解约束，未测任意输入资源上界；15 验证有序累积与依赖短路，不证明网络并行或提交一致性。全站生成由 root 集成。

