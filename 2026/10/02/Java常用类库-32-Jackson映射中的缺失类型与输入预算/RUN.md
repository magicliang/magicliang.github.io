# 第 32 篇复跑

本目录测试源与仓库 examples/java-libraries 中同名测试字节一致，使用完整工程运行，不能脱离 POM 单独 javac。

## 基础命令

从 examples/java-libraries 执行，分别使用 JDK8 与 JDK21：
```sh
./mvnw -B -ntp -s .mvn/settings.xml -Dtest=Chapter32Test clean verify
```

Maven Wrapper3.9.14；Zulu8.0.472、Corretto21.0.11；Java8 API。2026-10-02两环境各 4 次测试，失败/错误/跳过均0。完整原始XML与日志在 evidence/32/。
首次下载需要网络；缓存完整后可以增加 -o，使用其他仓库位置时增加 -Dmaven.repo.local=<路径>。并行运行使用独立工程副本，不共享target。
