# E06 复现实验

版本：Vavr 0.10.7 + Guava33.5.0-jre adapter。源码SHA：3af14df99c6a99ecd984e516d5f5294335cfbe84。

Java8源码基线，Zulu8u472与Corretto21.0.11均已实测。

从博客仓库根目录运行：

```sh
cd examples/java-libraries
./mvnw -B -ntp -Dtest=blog.libraries.Extension06Test test
```

首次运行需下载Maven依赖，切换JAVA_HOME即可选择JDK。测试在src/test/java中的位置按工程区分，现代章位于modern/src/test/java。附件完整测试与主工程文件逐字节相同。

独立正文程序为ParsedQuantity.java，LIBRARY_CP应设置为该工程实际运行classpath中的依赖JAR路径（见evidence/E06/jdk8-snippet.stdout.txt的实际命令；不同电脑需替换路径）：

```sh
javac -cp "$LIBRARY_CP" ParsedQuantity.java
java -cp ".:$LIBRARY_CP" ParsedQuantity
```

Option.map null=Some(null)，JDK map null=empty，Vavr->JDK->Guava转换合并空；Try NumberFormatException/AssertionError成Failure，合成LinkageError/InterruptedException同实例重抛；recover后0、toOption失败信息丢弃；List.prepend尾部同一实例、旧新size1/2、可变StringBuilder共享；Lazy成功supplier0->1->1。

输入均本地创建，不接外部生产服务。没有巨大文件或耗尽资源操作。

未执行边界：真实VM灾难、阻塞中断标记、Lazy失败缓存组合、集合性能未测。

证据：examples/java-libraries/evidence/E06/ 中的raw Maven stdout、JUnit XML、snippet日志、source-inspection.txt和claim-ledger.md。本文不以测试通过代替Hexo页面验收。
