# Kotlin 19 素材与复跑

`java-platform-boundary.svg` 对照 Java 未标注输入在 Kotlin 中的危险直接读取、显式校验和 SAM 同步回调。`kotlin-language-19.tar.gz` 含完整累计工程、Gradle Wrapper、RUN/VERSIONS 与 00–19 研究/原始实验记录；旁边的 `.sha256` 验证字节。

```bash
sha256sum -c kotlin-language-19.tar.gz.sha256
mkdir -p /tmp/kotlin-19-replay
tar -xzf kotlin-language-19.tar.gz -C /tmp/kotlin-19-replay
cd /tmp/kotlin-19-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

需要 JDK 21 与预缓存的依赖。仓库可运行 `bash examples/kotlin-language/verification/19.sh` 复核 Kotlin/Java 混合编译与 Java 类的 `javap` 签名。旧 CLI 未接入 JavaInputPort；无协程或真实网络。只有任务文本写入内存，标签虽经校验仍未保存。
