# 02 素材与累计工程

活工程位于 `examples/kotlin-language/`。`kotlin-language-02.tar.gz` 冻结当前完整累计源码、测试、Gradle Wrapper（JAR/脚本）、RUN/VERSIONS、00–02 的原始验证输出；上一章的归档仍是对应章节的独立快照。

```bash
sha256sum -c kotlin-language-02.tar.gz.sha256
tar -xzf kotlin-language-02.tar.gz
cd kotlin-language
./gradlew --no-daemon clean test
./gradlew --no-daemon run --args='batch alpha beta'
```

真实解包复跑、实际退出码与断言见仓库 `writing-plans/kotlin/verification/02/unpack.txt`。`verification/02-unstable-smartcast.kt` 是隔离的预期编译拒绝样本，不进入默认构建；镜像分发包必须通过 Wrapper 记录的官方 SHA 校验。
