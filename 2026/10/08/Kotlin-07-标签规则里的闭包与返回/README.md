# Kotlin 07 素材与复跑

`label-rules.svg` 展示两次同步查询对 `prefix` 的读取与调用次数。`kotlin-language-07.tar.gz` 包含 Wrapper、完整累计代码、RUN/VERSIONS 与 00–07 研究/原始实验记录；旁边的 `.sha256` 提供下载校验。

```bash
sha256sum -c kotlin-language-07.tar.gz.sha256
mkdir -p /tmp/kotlin-07-replay
tar -xzf kotlin-language-07.tar.gz -C /tmp/kotlin-07-replay
cd /tmp/kotlin-07-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

需要 JDK 21 与已缓存的 Gradle/Kotlin 依赖。`verification/07-nonlocal-return.kt` 放在默认源码集之外，只为验证非 inline 回调的编译拒绝；仓库中可用 `bash verification/07.sh` 重跑。没有异步任务或真实存储查询。
