# E05 实验

```bash
SCALA_LAB_JAVA_HOME=/path/to/jdk21 SCALA_LAB_CLI_JAR=/path/to/scala-cli-1.9.1.jar python3 examples/scala-lab/electives/run.py E05 --run-id my-e05
```

需要Scala Native 0.5.8官方要求的clang/系统工具。本机Apple clang 21.0.0，macOS aarch64，Scala 3.3.6。共享核心直接引用E04/Core.scala；最终通过记录为 `examples/scala-lab/electives/E05/evidence/20261002-e/`，运行前SHA清单包含该跨章源码。编译JVM使用JAVA_TOOL_OPTIONS=-Xmx2g（当前runner默认值，可显式覆盖）；这不控制Native程序自己的GC堆。不运行重复free或释放后读取。
