# Kotlin E07 复跑材料

`kotlin-language-E07.tar.gz` 包含到 E07 为止的 JVM 累计工程及独立 `abi-compat` 生产者、旧 Java/Kotlin 消费者。仅向本机新建 `/tmp` 目录发布三个小型 JAR，不修改全局 Maven 仓库、不部署。

```bash
sha256sum -c kotlin-language-E07.tar.gz.sha256
tar -xzf kotlin-language-E07.tar.gz
cd kotlin-language
./gradlew --no-daemon --offline clean test springTest loopbackTest packageTest
bash abi-compat/verify.sh /tmp/kotlin-e07-result
```

JDK 21、Gradle/Kotlin/Spring 测试依赖的本地缓存和隔离 PostgreSQL 16 工具链是复跑条件；实验脚本的 `source-2.0.0.txt`、`java-source-2.0.0.txt` 保存**预期编译拒绝**，非脚本成功退出的替代证据。真实日志见 `writing-plans/kotlin/verification/E07/`。
