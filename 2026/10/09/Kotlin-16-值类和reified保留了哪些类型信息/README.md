# Kotlin 16 素材与复跑

`task-id-boundaries.svg` 区分源码 `TaskId` 类型检查、当前生成字节码与 `reified` 的外层类型判断。`kotlin-language-16.tar.gz` 包含 00–16 累计工程、Wrapper、RUN/VERSIONS、逐篇来源和原始测试/字节码证据；旁边的 SHA-256 可核对字节。

```bash
sha256sum -c kotlin-language-16.tar.gz.sha256
mkdir -p /tmp/kotlin-16-replay
tar -xzf kotlin-language-16.tar.gz -C /tmp/kotlin-16-replay
cd /tmp/kotlin-16-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

离线运行要求本机 JDK 21 及缓存依赖。仓库内可单独运行 `bash examples/kotlin-language/verification/16.sh` 查看 `TaskId` 生成符号与编译拒绝诊断；`verification/16-invalid-types.kt` 只用于隔离负例，不能加入默认源码集。当前无 Java 消费者/性能测量/数据库实验证据。
