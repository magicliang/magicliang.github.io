# Kotlin 30 素材与复跑

`channel-completion-points.svg` 标出 send、receive、处理和 close/cancel 的不同完成点。`kotlin-language-30.tar.gz` 是完整累计工程、Wrapper、RUN/VERSIONS、研究和原始验证输出的本地快照；没有上传或部署。

```bash
sha256sum -c kotlin-language-30.tar.gz.sha256
mkdir -p /tmp/kotlin-30-replay
tar -xzf kotlin-language-30.tar.gz -C /tmp/kotlin-30-replay
cd /tmp/kotlin-30-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

离线命令要求本机缓存冻结的依赖版本。`verification/30/` 保存实际逐组测试、闸门与命令退出码；未运行跨进程可靠消息投递、真实网络或数据库事务。
