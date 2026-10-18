# Kotlin 26 素材与复跑

`dispatcher-blocking-boundary.svg` 区分调用方释放、专用工作者受阻、ThreadLocal 恢复与取消后底层实际退出。`kotlin-language-26.tar.gz` 包含累计工程、Wrapper、RUN/VERSIONS、研究和原始证据；它没有上传或部署。

```bash
sha256sum -c kotlin-language-26.tar.gz.sha256
mkdir -p /tmp/kotlin-26-replay
tar -xzf kotlin-language-26.tar.gz -C /tmp/kotlin-26-replay
cd /tmp/kotlin-26-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

离线运行需要相应精确版本依赖缓存。读者应以 `verification/26/` 中的实际退出码与断言为准；首轮构建失败的日志不是已验证版本组合的正例。本篇不处理真实网络或数据库操作的中断。
