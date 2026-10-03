# E02 实验

```bash
SCALA_LAB_JAVA_HOME=/path/to/jdk21 SCALA_LAB_CLI_JAR=/path/to/scala-cli-1.9.1.jar python3 examples/scala-lab/electives/run.py E02 --run-id my-e02
```

Scala 3.3.7、FS2 3.11.0、Cats Effect 3.5.7。最终通过证据：`examples/scala-lab/electives/E02/evidence/20261002-d/`。临时文件由实验自身创建、关闭和删除；5毫秒是注入的延迟，不是性能测试结果。最终源码使用 `IO.sleep(5.millis) *> IO(s.toInt)` 保持先延迟、后解析。
