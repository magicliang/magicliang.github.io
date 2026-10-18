# Kotlin 12 素材与独立复跑

`task-state-paths.svg` 标出本章已定义的业务允许路径。`kotlin-language-12.tar.gz` 含 Wrapper、完整累计工程、RUN/VERSIONS 和 00–12 的研究/原始实验记录；旁边的 `.sha256` 校验下载文件。

```bash
sha256sum -c kotlin-language-12.tar.gz.sha256
mkdir -p /tmp/kotlin-12-replay
tar -xzf kotlin-language-12.tar.gz -C /tmp/kotlin-12-replay
cd /tmp/kotlin-12-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

需要本机 JDK 21 及已经缓存的依赖。仓库内还可运行 `bash verification/12.sh` 复核隔离的 when 编译失败样本；不要把 `verification/12-missing-branch.kt` 放进默认源码集。顺序状态测试未证实真正并发取消或持久化。
