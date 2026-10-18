# Kotlin 33 素材与离线复跑

`json-boundaries.svg` 展示结构反序列化、可空字段解释和领域不变量之间的独立边界。归档包含累计工程、Wrapper、VERSIONS、研究及原始输出，不包括 HTTP 或数据库运行证明。

```bash
sha256sum -c kotlin-language-33.tar.gz.sha256
mkdir -p /tmp/kotlin-33-replay
tar -xzf kotlin-language-33.tar.gz -C /tmp/kotlin-33-replay
cd /tmp/kotlin-33-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

非法 CLI `./gradlew --offline --no-daemon --console=plain run --args=submit` 应非零退出。离线运行依赖事先缓存同版插件与运行库；不是“有归档就可离线下载”。完整退出码见仓库 `writing-plans/kotlin/verification/33/`。
