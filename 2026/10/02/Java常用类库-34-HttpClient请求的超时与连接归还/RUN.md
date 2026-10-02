# 第 34 篇复跑

本目录测试源与仓库 examples/java-libraries 中同名测试字节一致，使用完整工程运行，不能脱离 POM 单独 javac。

## 基础命令

从 examples/java-libraries 执行，分别使用 JDK8 与 JDK21：
```sh
./mvnw -B -ntp -s .mvn/settings.xml -Dtest=Chapter34Test clean verify
```

Maven Wrapper3.9.14；Zulu8.0.472、Corretto21.0.11；Java8 API。2026-10-02两环境各 4 次测试，失败/错误/跳过均0。完整原始XML与日志在 evidence/34/。
首次下载需要网络；缓存完整后可以增加 -o，使用其他仓库位置时增加 -Dmaven.repo.local=<路径>。并行运行使用独立工程副本，不共享target。

## Modern命令

仅JDK21执行，现代工程release17：
```sh
./mvnw -B -ntp -s .mvn/settings.xml -f modern/pom.xml -Dtest=Chapter34ModernTest clean verify
```

本章modern 2 次测试通过。modern POM以 -javaagent:${settings.localRepository}/org/mockito/mockito-core/5.20.0/mockito-core-5.20.0.jar 显式启用Mockito instrumentation。

## 本机端点与资源

只绑定127.0.0.1临时端口，不调用外网服务。若沙箱禁止socket，需要允许本机测试端点。端点、响应、客户端、线程池均在清理范围内；等待有期限。实验关闭自动重试。连接拒绝没有冒称connect timeout，connect timeout/TLS/代理/HTTP2未测试。modern用Java11 API在JDK21运行，不能放入Java8套件。
