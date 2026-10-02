# E02 复现实验

版本：Guava 33.5.0-jre。源码SHA：8868c096cfdabbe38170b6e395369c315cfb72a1。

Java8源码基线，Zulu8u472与Corretto21.0.11均已实测。

从博客仓库根目录运行：

```sh
cd examples/java-libraries
./mvnw -B -ntp -Dtest=blog.libraries.Extension02Test test
```

首次运行需下载Maven依赖，切换JAVA_HOME即可选择JDK。测试在src/test/java中的位置按工程区分，现代章位于modern/src/test/java。附件完整测试与主工程文件逐字节相同。

独立正文程序为QuantityView.java，LIBRARY_CP应设置为该工程实际运行classpath中的依赖JAR路径（见evidence/E02/jdk8-snippet.stdout.txt的实际命令；不同电脑需替换路径）：

```sh
javac -cp "$LIBRARY_CP" QuantityView.java
java -cp ".:$LIBRARY_CP" QuantityView
```

Ints.asList数组与set双向修改、add失败、toArray复制隔离；checkedCast越界IAE/saturatedCast上界；IntMath.checkedAdd与JDK Math.addExact溢出AE；负数DOWN/FLOOR、HALF_EVEN、UNNECESSARY；真实InputStream一次最多1字节读和Reader一次最多1字符；ByteStreams借入流不关闭，ByteSource内部打开后关闭，openStream由调用方关闭；中文UTF8跨短读解码；CharSource读取异常保留且Reader关闭。

输入均本地创建，不接外部生产服务。没有巨大文件或耗尽资源操作。

未执行边界：关闭自身再次失败、无效UTF8策略、巨大输入和性能未测；正文不把资源close当业务回滚。

证据：examples/java-libraries/evidence/E02/ 中的raw Maven stdout、JUnit XML、snippet日志、source-inspection.txt和claim-ledger.md。本文不以测试通过代替Hexo页面验收。
