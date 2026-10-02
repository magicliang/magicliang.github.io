# 第 35 篇复跑

本目录测试源与仓库 examples/java-libraries 中同名测试字节一致，使用完整工程运行，不能脱离 POM 单独 javac。

## 基础命令

从 examples/java-libraries 执行，分别使用 JDK8 与 JDK21：
```sh
./mvnw -B -ntp -s .mvn/settings.xml -Dtest=Chapter35Test clean verify
```

Maven Wrapper3.9.14；Zulu8.0.472、Corretto21.0.11；Java8 API。2026-10-02两环境各 7 次测试，失败/错误/跳过均0。完整原始XML与日志在 evidence/35/。
首次下载需要网络；缓存完整后可以增加 -o，使用其他仓库位置时增加 -Dmaven.repo.local=<路径>。并行运行使用独立工程副本，不共享target。

## Modern命令

仅JDK21执行，现代工程release17：
```sh
./mvnw -B -ntp -s .mvn/settings.xml -f modern/pom.xml -Dtest=Chapter35ModernTest clean verify
```

本章modern 3 次测试通过。modern POM以 -javaagent:${settings.localRepository}/org/mockito/mockito-core/5.20.0/mockito-core-5.20.0.jar 显式启用Mockito instrumentation。

## 预期失败的突变实验

```sh
./mvnw -B -ntp -s .mvn/settings.xml -Dchapter35.mutant=true -Dtest=Chapter35Test test
```

预期退出1，7次执行中恰好snapshotDoesNotFollowSourceChanges失败，实际[A,B]而预期[A]。mutant-maven.log与mutant-surefire.xml单独存档，不能计入正常绿色套件。随后删除该属性并重跑正常命令。本实验开关只用于演示回归检测，不用于生产。
