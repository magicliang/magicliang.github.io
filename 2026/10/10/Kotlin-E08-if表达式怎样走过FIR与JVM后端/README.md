# Kotlin E08 复跑材料

`kotlin-language-E08.tar.gz` 保存累计 Kotlin/JVM 工程与 `CompilerPhaseBoundaryTest`，另保留 E07 独立本地 Maven 消费者工程；无编译器源码仓库 checkout 或私有缓存。源码 blob 与来源响应 SHA、原始 `javap`、JUnit 和检查结果见仓库 `writing-plans/kotlin/verification/E08/`。

```bash
sha256sum -c kotlin-language-E08.tar.gz.sha256
tar -xzf kotlin-language-E08.tar.gz
cd kotlin-language
./gradlew --no-daemon --offline clean test springTest loopbackTest packageTest
javap -classpath build/classes/kotlin/main -p -c example.tasks.CommandParserKt
bash abi-compat/verify.sh /tmp/kotlin-e08-abi-result
```

需要 JDK 21、Gradle/Kotlin/Spring 缓存及 PostgreSQL 16 工具链；源码级 FIR/IR 实际 dump 与编译器插件运行不在这份复跑材料内。
