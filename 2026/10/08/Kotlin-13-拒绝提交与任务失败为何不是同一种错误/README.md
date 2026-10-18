# Kotlin 13 素材与复跑

`submission-outcomes.svg` 区分提交决策、存储故障与任务运行后的业务失败。`kotlin-language-13.tar.gz` 包含完整累计工程、Gradle Wrapper、RUN/VERSIONS、一手资料研究及 00–13 原始实验输出；`.sha256` 用于校验。

```bash
sha256sum -c kotlin-language-13.tar.gz.sha256
mkdir -p /tmp/kotlin-13-replay
tar -xzf kotlin-language-13.tar.gz -C /tmp/kotlin-13-replay
cd /tmp/kotlin-13-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

离线运行需要本机 JDK 21 与事先缓存的依赖。旧 CLI 尚未接入 `SubmissionDecision`，故 CLI 正反例是此前功能的回归，而不是本章新行为的接口演示。存储故障使用替身注入，默认 `TaskStore.putIfAbsent` 不保证并发原子性。
