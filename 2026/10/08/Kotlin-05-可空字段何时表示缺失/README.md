# Kotlin 05 素材与独立运行

`optional-note.svg` 说明缺键、null 与空串的分支；`kotlin-language-05.tar.gz` 包含 Wrapper、累计任务工程、RUN/VERSIONS、00–05 研究与原始实验记录。下载后在 JDK 21 及已缓存 Gradle/Kotlin 依赖的环境复跑：

```bash
sha256sum -c kotlin-language-05.tar.gz.sha256
mkdir -p /tmp/kotlin-05-replay
tar -xzf kotlin-language-05.tar.gz -C /tmp/kotlin-05-replay
cd /tmp/kotlin-05-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

`verification/05-nonnull-rejection.kt` 是隔离的编译拒绝样本，不能复制进默认源码集。仓库内用 `bash verification/05.sh` 复验其编译诊断；归档版的 `verification/05/` 留有原始输出。备注字段没有接入 CLI，也没有 HTTP/数据库/真实任务执行器。
