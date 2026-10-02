# 第 08 篇实验

Java 8 API；Guava 33.5.0-jre；JUnit 5.13.4；Maven Wrapper 3.9.14。

下载第 00 篇工程，或使用博客仓库的 examples/java-libraries。将相邻 Chapter08Test.java 放入 src/test/java/blog/libraries/。在工程根目录执行：

```sh
./mvnw -B -ntp -s .mvn/settings.xml -Dtest=Chapter08Test clean verify
```

分别将 JAVA_HOME 指向 JDK 8 和 JDK 21。首次运行需要访问 Maven Central；不要使用 -o，除非依赖已缓存。

验收：4 tests，failures=0，errors=0，skipped=0。测试输入、逐项预期与异常断言均在完整源文件内。实际留证环境为 Zulu 8.0.472、Corretto 21.0.11；原始输出与 XML 位于 examples/java-libraries/evidence/08/。这些是功能测试，不是性能基准。
