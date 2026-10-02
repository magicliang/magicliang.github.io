# 第 29 篇复跑

下载同目录 java-libraries-25-30.tar.gz，解开后进入 java-libraries-25-30。

```bash
tar -xzf java-libraries-25-30.tar.gz
cd java-libraries-25-30
./mvnw -B -ntp -s .mvn/settings.xml -Dtest=Chapter29Test test
./mvnw -B -ntp -s .mvn/settings.xml clean verify
```

首次运行需要联网下载 Maven 3.9.14 与固定依赖。JAVA_HOME 指向 JDK 8 或 JDK 21；项目源码保持 Java 8。包内含六章共 23 个测试、三个 IO helper、pom.xml 和 Maven Wrapper，不含缓存和 target。运行所需完整 imports 均在源码中；本页同目录 Java 文件与实验工程逐字节一致。

实际验证环境：Zulu 8.0.472 与 Corretto 21.0.11，macOS。各 JDK 完整运行均为 23 tests / 0 failures / 0 errors / 0 skipped。仅跑本章时测试数为 4。测试报告位于 target/surefire-reports；仓库原始证据位于 examples/java-libraries/evidence/29/。

独立包使用系列固定 POM，因此包含其他系列依赖，全部版本已锁定。没有访问生产凭据、业务目录或外部服务。26 的符号链接实验需要允许创建符号链接的文件系统；Windows 未运行，不应跳过后记为通过。

30 的解包器只支持 ZIP 与未压缩 TAR，要求可信父目录、稳定本地输入和私有工作目录中没有不可信并发写者。时间检查不是可抢占硬截止；元数据解析峰值内存、清理失败、进程崩溃、跨平台文件系统均未覆盖。
