# 完整系列与决策示例

将java-libraries-full.tar.gz解压后进入java-libraries；解压前用CHECKSUMS.sha256检查附件。首次需要JDK8或21与官方Maven Central网络。

第38篇旧jar仅供兼容性fork，不在正常POM依赖：

```bash
mkdir -p /tmp/java-libraries-guava-old
curl --fail --location https://repo.maven.apache.org/maven2/com/google/guava/guava/30.1.1-jre/guava-30.1.1-jre.jar --output /tmp/java-libraries-guava-old/guava-30.1.1-jre.jar
./mvnw -B -ntp -s .mvn/settings.xml -DoldGuavaJar=/tmp/java-libraries-guava-old/guava-30.1.1-jre.jar clean verify
java -cp target/classes blog.libraries.LibraryDecisionDemo
```

切换JDK后使用clean verify；旧jar放在target外，clean不会删除它。路径参数oldGuavaJar由Chapter38Test读取，旧jar只进入兼容性fork。

现代/处理器/基准独立入口与兼容要求见工程README。主线8/21已验证，现代及JMH只实际21；更高目标依赖不能运行Java8。示例工程不是生产应用POM；不要直接把全部候选与测试provider带入生产。
