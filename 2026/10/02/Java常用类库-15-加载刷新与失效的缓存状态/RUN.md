# Chapter 15

主工程：仓库 `examples/java-libraries`，Guava33.5.0-jre，Wrapper3.9.14。分别在JDK8和21运行：

```bash
./mvnw -B -ntp -s .mvn/settings.xml -Dtest=Chapter15Test test
./mvnw -B -ntp -s .mvn/settings.xml org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath -DincludeScope=compile -Dmdep.outputFile=target/classpath.txt
javac -cp "$(cat target/classpath.txt)" -d target /path/to/RefreshTimeline.java
java -ea -cp "target:$(cat target/classpath.txt)" RefreshTimeline
```

`/path/to/RefreshTimeline.java`替换为所下载的单文件示例路径。Windows使用分号作为classpath分隔符；Windows运行NOT_RUN。

实验包含五项契约测试和单文件刷新时间线。注入刷新失败会产生警告与异常栈，这是预期反例输出；JUnit应当五项通过，单文件输出 `idle=0 reload, pending=v1, completed=v2`。

完整证据保存在主工程evidence/15，包含两JDK的stdout和Surefire XML。其他平台、弱引用GC、吞吐量与完整业务更新围栏没有运行。复制此测试到相同固定依赖工程后执行；不能只用Guava单个jar替代其依赖classpath。
