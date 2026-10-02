# 17 复现实验

固定 Guava 33.5.0-jre，Java 8源码基线；实测 Zulu 8u472、Corretto21.0.11。完整测试为 Chapter17Test.java，独立正文示例为 RateTiming.java。

在博客仓库根目录运行（不部署）：

```sh
cd examples/java-libraries
./mvnw -B -ntp -Dtest=com.google.common.util.concurrent.Chapter17Test test
```

设置 JAVA_HOME 后分别用 Java8、21执行。首次运行需要下载依赖。Maven的完整工程、wrapper和JUnit依赖由系列examples/java-libraries提供；附件测试不是脱离工程直接运行的main类。测试进入Guava同包以访问包级SleepingStopwatch，只用于检验固定版本时间模型，不建议业务依赖内部API。

正文示例可用 Guava 与 failureaccess 的jar作为classpath：

```sh
javac -cp "$LIBRARY_CP" RateTiming.java
java -cp ".:$LIBRARY_CP" RateTiming
```

LIBRARY_CP需包含Guava33.5.0-jre与failureaccess1.0.3 jar的实际路径；Windows使用分号分隔classpath。所有输入均由测试本地创建，无外部服务。测试进程的临时线程池由finally关闭。

LAB：4项测试：确定模型rate2 acquire(4),acquire(),acquire()等待0/2/.5秒；idle3秒后2个存储许可与随后1个新许可零等待，try499ms失败/500ms成功；warmup rate2/period4s/cold3等待0/1.375/1.125/.875/.625/.5；真实时钟测acquire(3)，记录计划与elapsed；3并发线程在完成前均取得许可，Semaphore2第三次失败。SOURCE：RateLimiter/SmoothRateLimiter及上游RateLimiterTest。NOT_RUN：动态setRate、全线程交错公平性、分布式配额与严格滑窗；未将假时钟当真实时间。真实测量保留初次执行raw logs，不把一次调度误差推广成保证。

原始命令输出、JUnit XML、来源账本与源码核查位于仓库 examples/java-libraries/evidence/17/。真实时间与随机样本输出不能解释为跨环境性能或概率保证。
