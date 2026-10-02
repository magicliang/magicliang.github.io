# 第 13 篇复跑

环境：Java 8 或 Java 21，Guava 33.5.0-jre，JUnit 5.13.4，Maven Wrapper 3.9.14。

1. 使用系列实验工程 examples/java-libraries；也可下载第 00 篇的基础工程压缩包。
2. 将本页下载的 Chapter13Test.java 放到 src/test/java/blog/libraries/，保留 package blog.libraries。
3. 在工程根目录执行：

```sh
./mvnw -B -ntp -s .mvn/settings.xml -Dtest=Chapter13Test clean verify
```

首次执行需要从 Maven Central 下载依赖。不要把 -o 用于空缓存。JDK 通过 JAVA_HOME 选择。

预期：Tests run: 4, Failures: 0, Errors: 0, Skipped: 0。测试源码包含所有 import，使用 Java 8 API。完整测试报告位于 target/surefire-reports/。本章没有外部服务、并发或性能基准。
