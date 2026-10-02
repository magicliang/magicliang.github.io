# 第 02 篇实验

状态：`LAB_VERIFIED`，环境为 Scala 3.3.7、Corretto JDK 21.0.11、Scala CLI 1.9.1 / sbt 1.11.7。

```sh
export SCALA_LAB_JAVA_HOME=/path/to/jdk-21
python3 examples/scala-lab/run.py chapter 02 --run-id local
python3 examples/scala-lab/run.py negative --run-id local
python3 examples/scala-lab/run.py sbt --run-id local
python3 examples/scala-lab/run.py bytecode --run-id local
```

本次通过统一 all 与 sbt 入口执行。证据：`examples/scala-lab/evidence/20261002-batch01/all.log`、`sbt.log`、`negative-02-val-reassignment.log` 及同名 JSON；成功入口 exit=0，反例 exit=1 且匹配 Reassignment to val。

实测计数：source 总调用 7 次；lazy 首次失败、第二次成功、随后缓存，总尝试 2 次；两个线程读取局部 lazy 得到 99，初始化次数 1。线程均设超时并关闭线程池。

局部字节码 `bytecode-02.log` 与 JSON 为 `LAB_VERIFIED`，exit=0，匹配 LazyInt、initialized、initialize 和 monitorenter。固定源码结构为 `SOURCE_VERIFIED`；递归死锁、成员字段字节码、本章 lazy 实现的 Scala.js 对照和 @threadUnsafe 为 `NOT_RUN`。E04 另有共享纯核心的实际 Scala.js 运行，不能替代这里的 lazy 对照。一次线程调度不能证明所有竞争路径覆盖。
