# Kotlin 22 素材与复跑

`task-contract-evidence.svg` 区分正常 JUnit、独立编译拒绝和仍未覆盖的真实竞态/外部 IO。`kotlin-language-22.tar.gz` 含 00–22 累计双模块源码、Wrapper、RUN/VERSIONS 及必要的原始验证记录；`.sha256` 检验打包字节。这里没有注入不稳定 sleep 或网络依赖。

```bash
sha256sum -c kotlin-language-22.tar.gz.sha256
mkdir -p /tmp/kotlin-22-replay
tar -xzf kotlin-language-22.tar.gz -C /tmp/kotlin-22-replay
cd /tmp/kotlin-22-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

离线需要 JDK 21 与本机已缓存依赖。完整仓库中运行 `bash examples/kotlin-language/verification/22.sh` 另外验证独立 `22-incomplete-state.kt` 编译拒绝和旧 16 负例脚本的新版工程复跑。默认源码集中只有能通过编译的行为测试，其余历史隔离脚本没有在这一篇全部复验。
