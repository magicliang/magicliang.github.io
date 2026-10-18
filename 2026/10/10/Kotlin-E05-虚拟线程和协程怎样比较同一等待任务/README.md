# Kotlin E05 复跑材料

`kotlin-language-E05.tar.gz` 包含 Kotlin/JVM 累计工程、原 00–39 测试、E02–E04 跨目标源码与独立的 E05 虚拟线程/协程对照 JUnit 任务；不含 E01 尚未验证的 Android 项目、生成目录或本地缓存。归档 SHA 在同名 `.sha256` 文件。

```bash
sha256sum -c kotlin-language-E05.tar.gz.sha256
tar -xzf kotlin-language-E05.tar.gz
cd kotlin-language
./gradlew --offline --no-daemon --console=plain clean test loopbackTest packageTest jmh comparisonTest
```

JDK 21、Gradle/Kotlin/coroutines/JMH 已缓存依赖是离线复跑条件。`comparisonTest` 的结果断言检查校验和、最多 32 个在途任务以及显式停止；纳秒级耗时仅是本机短测量，重跑不应要求与文中数字相同。E01 Android 与生产负载未运行。
