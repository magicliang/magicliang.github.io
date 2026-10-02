# 第 23 篇实验复跑

此目录的 Chapter23Test.java 与系列工程 src/test/java/blog/libraries/Chapter23Test.java 字节一致。完整工程位于仓库 examples/java-libraries；单个测试源不能脱离 POM 和 JUnit 依赖独立执行。

## 命令

从完整工程目录执行：

```sh
./mvnw -B -ntp -s .mvn/settings.xml -Dtest=Chapter23Test clean verify
```

分别将 JAVA_HOME 指向 JDK 8 与 JDK 21 重复执行。首次运行需要从 Maven Central 下载 Wrapper 分发包与依赖。不要让两个进程写同一个 target；每个运行环境使用独立副本或顺序执行。

## 已运行结果

2026-10-02：Zulu 8.0.472、Corretto 21.0.11；Maven 3.9.14，Java 8 API 编译。Commons Lang 3.20.0、Commons Collections 4.6.0、Guava 33.5.0-jre；JUnit 5.13.4。本章两环境各 tests=4、failures=0、errors=0、skipped=0。与 20–24 合并批次的命令退出码均为 0，共 20 tests。

证据位于 examples/java-libraries/evidence/23/：jdk8-surefire.xml、jdk21-surefire.xml 保存真实版本、classpath、测试方法和计数；jdk8-maven.log、jdk21-maven.log 为原始日志；claim-ledger.md 区分 DOC、SOURCE、LAB、NOT_RUN。

本实验验证指定输入下的功能契约，不包含吞吐、内存、并发负载测试；读者改动练习没有计入通过数量。
