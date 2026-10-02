# 第 33 篇复跑

本目录测试源与仓库 examples/java-libraries 中同名测试字节一致，使用完整工程运行，不能脱离 POM 单独 javac。

## 基础命令

从 examples/java-libraries 执行，分别使用 JDK8 与 JDK21：
```sh
./mvnw -B -ntp -s .mvn/settings.xml -Dtest=Chapter33Test clean verify
```

Maven Wrapper3.9.14；Zulu8.0.472、Corretto21.0.11；Java8 API。2026-10-02两环境各 5 次测试，失败/错误/跳过均0。完整原始XML与日志在 evidence/33/。
首次下载需要网络；缓存完整后可以增加 -o，使用其他仓库位置时增加 -Dmaven.repo.local=<路径>。并行运行使用独立工程副本，不共享target。

## 隔离日志实验

工程的两个test provider仅用于构造不同fork classpath，不是应用部署推荐。测试内部启动五个独立JVM：none、simple、jdk14、multiple、bridge。target/chapter33-forks保存各自command/stdout/stderr；multiple必须实际发现2个provider，断言不预设谁胜出；bridge仅JUL→SLF4J→simple。主suite可能输出多provider诊断，不能代替fork证据。子进程有20秒期限，MDC finally清理。
