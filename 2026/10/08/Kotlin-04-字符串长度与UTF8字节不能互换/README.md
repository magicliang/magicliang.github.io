# Kotlin 04 素材与复跑

`length-units.svg` 是本篇的计数图；`kotlin-language-04.tar.gz` 是包含 Wrapper、完整累计 Kotlin 工程、`RUN.md`、`VERSIONS.md` 和截至 04 的研究/实验记录的快照。校验文件与归档同目录。

```bash
sha256sum -c kotlin-language-04.tar.gz.sha256
mkdir -p /tmp/kotlin-04-replay
tar -xzf kotlin-language-04.tar.gz -C /tmp/kotlin-04-replay
cd /tmp/kotlin-04-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit 检索🙂'
./gradlew --offline --no-daemon --console=plain run --args=submit  # 预期非零
```

本机 JDK 21、Gradle/Kotlin 依赖已缓存是 `--offline` 的前提；离线首次解析失败不等于单元测试失败。`verification/04/` 保留原始命令/退出码与断言；正文未宣称文件、HTTP 或数据库已接入。
