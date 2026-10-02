# Play 00–08 累计工程重跑说明

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
```

launcher SHA-256：3cca02818047327a83efde776103a1ef92f76f72c062badbbb062499a3270c07。

预期：累计JUnit 12/12；原verify开发和生产各56请求，pipeline_checks复用回归并增加31组实验，各118请求。路由、模板与dependsOn三个单变量反例均为编译失败；首批反例记录保留在batch00-05。本批Action/Filter/parser的真实状态、正文、头、阶段与字节观测在evidence/batch06-08。

HTTP 只监听 127.0.0.1 的空闲端口，密钥随机且不保存。finally 终止启动进程，受控 SIGTERM 退出通常143。负例临时副本自动清理。有限实验队列、观测接口和合成请求 CSRF bypass 不用于生产。

deferred拒绝与解析流失败已验证；数据库、真实TCP断连资源释放、完整优雅退出和压测仍NOT_RUN。完整说明、固定版本和原始证据在压缩包中，重跑覆盖解压目录内证据，不修改博客正文。00–05的历史实验结论保持原批范围，下载包则随累计工程更新。
