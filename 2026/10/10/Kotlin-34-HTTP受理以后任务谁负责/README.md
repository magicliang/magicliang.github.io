# Kotlin 34 素材与复跑

`http-task-lifecycle.svg` 将 HTTP 受理、后台 Job 和查询状态分开；归档含累计源码、Wrapper、VERSIONS、research 与 verification 日志。不含数据库或线上部署材料。

```bash
sha256sum -c kotlin-language-34.tar.gz.sha256
mkdir -p /tmp/kotlin-34-replay
tar -xzf kotlin-language-34.tar.gz -C /tmp/kotlin-34-replay
cd /tmp/kotlin-34-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test loopbackTest
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

非法 CLI `./gradlew --offline --no-daemon --console=plain run --args=submit` 预期非零退出。离线复跑需提前缓存 Ktor `3.3.1` 及全部传递依赖；页面测试不是发布环境验收。真实端口闸门/网络中途断线未完成，见 `writing-plans/kotlin/verification/34/build-initial.txt`。
