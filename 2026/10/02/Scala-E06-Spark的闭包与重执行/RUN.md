# E06 实验

```bash
SCALA_LAB_JAVA_HOME=/path/to/jdk21 SCALA_LAB_CLI_JAR=/path/to/scala-cli-1.9.1.jar python3 examples/scala-lab/electives/run.py E06 --run-id my-e06
```

Scala 2.13.16、Spark Core 4.0.0、JDK21、local[2]。case.json显式记录4项JDK模块开放参数。通过证据为 `examples/scala-lab/electives/E06/evidence/20261002-c/`；b中的序列化诊断器JDK访问失败不是目标拒绝成功。只验证两次action重算，未进行真实集群故障注入。
