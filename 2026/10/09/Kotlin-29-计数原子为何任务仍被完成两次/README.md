# Kotlin 29 素材与复跑

`task-index-update.svg` 区分丢失更新、单字段原子性和任务状态/计数的复合互斥。`kotlin-language-29.tar.gz` 提供累计工程、Gradle Wrapper、RUN/VERSIONS、研究和原始证据；不是部署制品。

```bash
sha256sum -c kotlin-language-29.tar.gz.sha256
mkdir -p /tmp/kotlin-29-replay
tar -xzf kotlin-language-29.tar.gz -C /tmp/kotlin-29-replay
cd /tmp/kotlin-29-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

离线运行需要先缓存精确依赖。`verification/29/` 记录实际命令、JUnit、退出码和原始断言；虚拟交错不能替代真实线程压力或数据库事务实验。
