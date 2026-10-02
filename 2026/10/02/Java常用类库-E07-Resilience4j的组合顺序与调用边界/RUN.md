# E07 复现实验

版本：Resilience4j 2.3.0。源码SHA：c2c6575114fc0650177fb21e1ff967f14acde39c。

现代实验使用JDK21，编译目标release17；不支持Java8。

从博客仓库根目录运行：

```sh
cd examples/java-libraries
./mvnw -f modern/pom.xml -B -ntp -Dtest=blog.libraries.Extension07Test test
```

首次运行需下载Maven依赖，切换JAVA_HOME即可选择JDK。测试在src/test/java中的位置按工程区分，现代章位于modern/src/test/java。附件完整测试与主工程文件逐字节相同。

独立正文程序为RetryOrder.java，LIBRARY_CP应设置为该工程实际运行classpath中的依赖JAR路径（见evidence/E07/jdk21-snippet.stdout.txt的实际命令；不同电脑需替换路径）：

```sh
javac --release 17 -cp "$LIBRARY_CP" RetryOrder.java
java -cp ".:$LIBRARY_CP" RetryOrder
```

真实受控函数Retry(Breaker(call))1次物理调用后OPEN；Breaker(Retry(call))3次后成功且breaker统计success1/fail0；周期RateLimiter2true1false；真实2线程Bulkhead active峰值2、第三拒绝、释放后slots2；显式HALF_OPEN一探测额，成功CLOSED失败OPEN；TimeLimiter25ms+Retry2+真实CompletableFuture供应任务：sideEffects2、超时后任务未完成、释放后结束且interrupt0。

输入均本地创建，不接外部生产服务。线程由latch控制并在finally关闭，25ms仅为观察超时；5秒保护不是业务SLA。

未执行边界：Java8不兼容，Java17只编译目标未实际运行；modern JDK21实测。自动OPEN等待时钟、远程HTTP取消/事务、全部装饰排列、分布式配额、生产日志未测。

证据：examples/java-libraries/evidence/E07/ 中的raw Maven stdout、JUnit XML、snippet日志、source-inspection.txt和claim-ledger.md。本文不以测试通过代替Hexo页面验收。
