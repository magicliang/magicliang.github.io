# 第 04 篇实验

使用系列第 00 篇附件提供的 Maven 工程，将本目录 Chapter04Test.java 放到 src/test/java/blog/libraries/。依赖为 Guava 33.5.0-jre、Commons Lang 3.20.0、JUnit Jupiter 5.13.4，Maven Wrapper 3.9.14；不要把测试源放到 src/main/java。

在工程根目录执行：

```bash
./mvnw -B -ntp -s .mvn/settings.xml -Dtest=Chapter04Test clean verify
```

设置 JAVA_HOME 后分别在 Java 8 与 Java 21 执行；首次需要从 Maven Central 下载依赖。文章正文内的独立 main 示例是另一条可执行路径，需把 Guava/Commons JAR 加入 classpath（仅 JDK 的例子不需要）。

场景：五组 ASCII 输入等价、U+00A0/U+001C 反例、三实现 null 拒绝、ROOT/土耳其语大小写与 ß 扩张。

本次环境：Zulu 1.8.0_472、Corretto 21.0.11，macOS。原始验收位于仓库 examples/java-libraries/evidence/04/，包含两个 JDK 的 Surefire XML 和 stdout。没有运行性能或并发实验，正文未提出相应验证结论。
