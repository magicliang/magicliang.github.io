# E03 复跑

下载 java-libraries-extensions.tar.gz，解包后进入同名目录。

```bash
tar -xzf java-libraries-extensions.tar.gz
cd java-libraries-extensions
./mvnw -B -ntp -s .mvn/settings.xml clean verify
```

首次运行需从 Maven Central 下载固定依赖；本实验已在 Zulu 8.0.472 与 Corretto 21.0.11 分别验证。JAVA_HOME 指向所选 JDK。扩展包含E03/E04/E05共10个测试；单章可增加 -Dtest=Extension03Test。本章 3 tests / 0 failures / 0 errors / 0 skipped。raw stdout/XML 位于仓库 examples/java-libraries/evidence/E03/。

JOL未获得Instrumentation/SA，输出仅为对象图布局估计，不是GC retained heap。JMH结果复用36真实运行，类型是int→Object，同样本1024预构建命中查询；不是新跑的所有吞吐场景。
