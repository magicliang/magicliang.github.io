# 18 复现实验

固定 Guava 33.5.0-jre，Java 8源码基线；实测 Zulu 8u472、Corretto21.0.11。完整测试为 Chapter18Test.java，独立正文示例为 FilteredCatalog.java。

在博客仓库根目录运行（不部署）：

```sh
cd examples/java-libraries
./mvnw -B -ntp -Dtest=blog.libraries.Chapter18Test test
```

设置 JAVA_HOME 后分别用 Java8、21执行。首次运行需要下载依赖。Maven的完整工程、wrapper和JUnit依赖由系列examples/java-libraries提供；附件测试不是脱离工程直接运行的main类。

正文示例可用 Guava 与 failureaccess 的jar作为classpath：

```sh
javac -cp "$LIBRARY_CP" FilteredCatalog.java
java -cp ".:$LIBRARY_CP" FilteredCatalog
```

LIBRARY_CP需包含Guava33.5.0-jre与failureaccess1.0.3 jar的实际路径；Windows使用分号分隔classpath。所有输入均由测试本地创建，无外部服务。测试进程的临时线程池由finally关闭。

LAB：2项测试：SHA256空串/abc已知向量；中文UTF8与JDK MessageDigest一致；putInt小端序；字段无边界拼接反例与长度前缀；Random seed20261002、expected1000/fpp.01、实际1000/10000、精确LinkedHashSet真值、10000个不相交查询，误判110/9949，重复插入不改bits，已插入无阴性。SOURCE：BloomFilter/AbstractByteHasher/BloomFilterStrategies。DOC：版本化BloomFilter、NIST示例向量列表。NOT_RUN：密码存储、真实性能、所有输入分布或种子的概率保证；固定种子统计仅为本样本。

原始命令输出、JUnit XML、来源账本与源码核查位于仓库 examples/java-libraries/evidence/18/。真实时间与随机样本输出不能解释为跨环境性能或概率保证。
