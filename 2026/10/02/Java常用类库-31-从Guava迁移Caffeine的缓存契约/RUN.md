# 缓存迁移实验

本篇使用完整示例工程的modern模块，Caffeine3.2.4/Guava33.5.0-jre；release17，实际JDK21运行。Java8不适用。

从系列工程examples/java-libraries运行：

```sh
MAVEN_USER_HOME="$PWD/.maven-user-home" ./mvnw -B -ntp -s .mvn/settings.xml -f modern/pom.xml -Dtest=Chapter31Test verify
```

默认使用自己的Maven本地仓库；原始实验用-Dmaven.repo.local=/tmp/java-libraries-m2。首次在线下载，之后可加-o。Chapter31Test.java应位于modern/src/test/java/blog/libraries，完整工程已包含该文件。

CacheMigrationDemo.java是完整运行类，在modern/src/main/java/blog/libraries。获取运行classpath后执行：

```sh
MAVEN_USER_HOME="$PWD/.maven-user-home" ./mvnw -B -ntp -s .mvn/settings.xml -f modern/pom.xml org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath -Dmdep.outputFile=target/classpath.txt
java -cp "modern/target/classes:$(cat modern/target/classpath.txt)" blog.libraries.CacheMigrationDemo
```

预期输出refresh-result=late, cache=absent。七项JUnit测试覆盖缺失/异常、刷新、失效、同键线程、共享future取消、移除通知、统计/过期/容量。实验中的direct executor是假时钟和可控future的确定性设置；不证明网络请求已经中断或默认执行器的压力性能。

原始证据位于evidence/31：日志、JUnit XML、源码摘录和claim-ledger。构建返回0且7tests/0failures/0errors/0skipped；日志保留预期刷新异常。JDK11/17实际执行、其他OS与性能未运行。
