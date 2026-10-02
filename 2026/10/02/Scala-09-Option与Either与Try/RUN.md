# 第 09 篇实验

状态：LAB_VERIFIED。Scala 3.3.7 / 标准库 2.13.16 / Scala CLI 1.9.1 / JDK 21.0.11-amzn。

在仓库根目录执行：

```bash
export SCALA_LAB_JAVA_HOME=/Users/magicliang/.sdkman/candidates/java/21.0.11-amzn
export SCALA_LAB_CLI_JAR=/private/tmp/scala-lab-cli-1.9.1.jar
python3 examples/scala-lab/run.py chapter 09 --run-id 20261002-ch09
python3 examples/scala-lab/run.py negative 09 --run-id 20261002-ch09
```

正例源码：examples/scala-lab/snippets/09/Chapter09.scala；入口 scalaexamples.Chapter09。实际退出码 0，实际输出：

```text
bad=None,Left(Malformed),Failure(NumberFormatException);calls=0;interrupt=escaped
```

证据：examples/scala-lab/evidence/20261002-ch09/09.log 和 09.json。环境见同目录 environment.txt。

- wrong-error-channel：negative/09/wrong-error-channel/case.json 指定诊断逐项匹配，实际退出码 1；证据 negative-09-wrong-error-channel.log/.json。



统一 runner 每次先校验 Maven 工具 SHA，需网络；已缓存依赖不代表这一步离线。首次 08 正例因部分函数单行语法失败，修正为缩进块后重跑了完整正反例，上述为修正后结果。全站构建与页面检查由整批集成负责，本目录不冒充其证据。

