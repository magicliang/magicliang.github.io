# Play 00–17 累计工程重跑说明

解压同目录 play-lab-source.zip，在 play-lab/ 中执行。需要 JDK 21、Python 3、首次依赖下载所需网络；不需要 Docker 或全局 sbt。

```bash
export JAVA_HOME=/path/to/jdk-21
mkdir -p .tools
curl -fL https://repo.maven.apache.org/maven2/org/scala-sbt/sbt-launch/1.10.7/sbt-launch-1.10.7.jar -o .tools/sbt-launch-1.10.7.jar
shasum -a 256 .tools/sbt-launch-1.10.7.jar
bash sbtw test stage
python3 lab/verify.py --dev
python3 lab/verify.py
python3 lab/verify.py --negative
python3 lab/pipeline_checks.py --dev
python3 lab/pipeline_checks.py
python3 lab/content_checks.py --dev
python3 lab/content_checks.py
python3 lab/async_checks.py --dev
python3 lab/async_checks.py
python3 lab/stream_checks.py --evidence evidence/batch18-21/replay
```

launcher SHA-256：3cca02818047327a83efde776103a1ef92f76f72c062badbbb062499a3270c07。

预期：累计JUnit39/39；原verify两模式各56请求，pipeline_checks各118请求，content_checks各185请求/37组内容检查，async_checks各198请求/10组异步与3组预算检查。最新共享证据在batch12-17；JSON/Form/Twirl/Assets历史证据在batch09-11，真实浏览器记录独立保存；Html(Int)临时编译反例退出1。首批三个单变量编译反例仍保留在batch00-05。

HTTP 只监听 127.0.0.1 的空闲端口，密钥随机且不保存。finally 终止启动进程，受控 SIGTERM 退出通常143。负例临时副本自动清理。有限实验队列、观测接口和合成请求 CSRF bypass 不用于生产。

最新累计JUnit39/39；流与文件共享证据在batch18-21。真实TCP断连、SSE重连、WS半关闭和上传/下载清理已验证；stream_checks要求19018端口空闲，重放五组有限socket并停止自有进程。数据库、完整优雅退出和压测仍NOT_RUN。完整说明、版本和证据在压缩包中，重跑覆盖解压目录内证据。00–05历史结论保持原批范围，下载包随累计工程更新。
