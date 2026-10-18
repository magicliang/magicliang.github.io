# Kotlin 15 素材与复跑

`state-variance.svg` 对照只读源 `out`、接收器 `in`、星投影后的逐层校验。`kotlin-language-15.tar.gz` 包含完整累计工程、Gradle Wrapper、RUN/VERSIONS、00–15 一手资料与原始实验日志；`.sha256` 用于校验完整性。

```bash
sha256sum -c kotlin-language-15.tar.gz.sha256
mkdir -p /tmp/kotlin-15-replay
tar -xzf kotlin-language-15.tar.gz -C /tmp/kotlin-15-replay
cd /tmp/kotlin-15-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

JDK 21 和已缓存的 Gradle 依赖是离线复跑前提。仓库内 `bash examples/kotlin-language/verification/15.sh` 另编译 `verification/15-invalid-generic-checks.kt` 保存预期拒绝诊断；不要将失败样本放进默认源码集。工程没有接入真实数据库、协程或 Java 适配。
