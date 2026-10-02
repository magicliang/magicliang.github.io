# 16 复现实验

固定 Guava 33.5.0-jre，Java 8源码基线；实测 Zulu 8u472、Corretto21.0.11。完整测试为 Chapter16Test.java，独立正文示例为 FutureTransform.java。

在博客仓库根目录运行（不部署）：

```sh
cd examples/java-libraries
./mvnw -B -ntp -Dtest=blog.libraries.Chapter16Test test
```

设置 JAVA_HOME 后分别用 Java8、21执行。首次运行需要下载依赖。Maven的完整工程、wrapper和JUnit依赖由系列examples/java-libraries提供；附件测试不是脱离工程直接运行的main类。

正文示例可用 Guava 与 failureaccess 的jar作为classpath：

```sh
javac -cp "$LIBRARY_CP" FutureTransform.java
java -cp ".:$LIBRARY_CP" FutureTransform
```

LIBRARY_CP需包含Guava33.5.0-jre与failureaccess1.0.3 jar的实际路径；Windows使用分号分隔classpath。所有输入均由测试本地创建，无外部服务。测试进程的临时线程池由finally关闭。

LAB：4项测试：回调成功/失败与catalog-callback线程；transform结果5；direct监听器阻塞catalog-setter但源已done；完成后注册由注册线程执行；派生取消传播到源；执行器拒绝成为派生失败；Guava任务cancel(true)收到中断，而已开始的CompletableFuture supplier取消未被中断。SOURCE：AbstractTransformFuture/AbstractFuture/ListenableFuture。DOC：版本化ListenableFuture与JDK8 CompletableFuture.cancel。NOT_RUN：transformAsync展开、所有Future实现的普遍取消行为，不据此推断。

原始命令输出、JUnit XML、来源账本与源码核查位于仓库 examples/java-libraries/evidence/16/。真实时间与随机样本输出不能解释为跨环境性能或概率保证。
