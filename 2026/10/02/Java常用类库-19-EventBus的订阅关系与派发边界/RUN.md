# 19 复现实验

固定 Guava 33.5.0-jre，Java 8源码基线；实测 Zulu 8u472、Corretto21.0.11。完整测试为 Chapter19Test.java，独立正文示例为 ExplicitCatalogListeners.java。

在博客仓库根目录运行（不部署）：

```sh
cd examples/java-libraries
./mvnw -B -ntp -Dtest=blog.libraries.Chapter19Test test
```

设置 JAVA_HOME 后分别用 Java8、21执行。首次运行需要下载依赖。Maven的完整工程、wrapper和JUnit依赖由系列examples/java-libraries提供；附件测试不是脱离工程直接运行的main类。

正文示例可用 Guava 与 failureaccess 的jar作为classpath：

```sh
javac -cp "$LIBRARY_CP" ExplicitCatalogListeners.java
java -cp ".:$LIBRARY_CP" ExplicitCatalogListeners
```

LIBRARY_CP需包含Guava33.5.0-jre与failureaccess1.0.3 jar的实际路径；Windows使用分号分隔classpath。所有输入均由测试本地创建，无外部服务。测试进程的临时线程池由finally关闭。

LAB：3项测试：默认同步重入顺序parent-start,parent-end,child@main；普通异常handler一次且其他订阅执行，post返回；重复注册同一对象一次回调；注销前后DeadEvent与重复注销异常。SOURCE：EventBus官方avoid建议、Dispatcher线程局部队列、Subscriber Error重抛和局部同步、SubscriberRegistry快照。DOC：官方EventBus说明及issue7728反向核验Error。NOT_RUN：AsyncEventBus、并发注销交错、AllowConcurrentEvents交错、Error分支运行；正文明确这些只由源码或未执行范围支持。

原始命令输出、JUnit XML、来源账本与源码核查位于仓库 examples/java-libraries/evidence/19/。真实时间与随机样本输出不能解释为跨环境性能或概率保证。
