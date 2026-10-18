# Kotlin 25 素材与复跑

`managed-task-tree.svg` 把服务 owner、一次任务的子树和未验收的跨任务隔离标在不同层。`kotlin-language-25.tar.gz` 包含累计工程、Wrapper、RUN/VERSIONS、研究与证据，不是部署或上传制品。

```bash
sha256sum -c kotlin-language-25.tar.gz.sha256
mkdir -p /tmp/kotlin-25-replay
tar -xzf kotlin-language-25.tar.gz -C /tmp/kotlin-25-replay
cd /tmp/kotlin-25-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

离线命令要求预先缓存冻结依赖；`verification/25/build-initial.txt` 的对象身份断言失败不能误记作正例。真网络、数据库与线程阻塞操作的停止均 **NOT_RUN**。
