# JMH 1.37 可复跑基准

完整工程路径examples/java-libraries/benchmarks，需JDK17以上；本次实际JDK21。

从examples/java-libraries执行：

```bash
./mvnw -B -ntp -s .mvn/settings.xml -f benchmarks/pom.xml clean package
java -jar benchmarks/target/benchmarks.jar blog.libraries.LibraryBenchmarks -f 2 -wi 2 -i 3 -w 1s -r 1s -t 1 -prof gc -rf json -rff benchmarks/target/jmh-result.json
```

首次运行需要官方Central依赖。JMH需要本地fork协调socket；禁止socket的sandbox会失败，这种日志不算性能结果。JSON与stdout是本次实际完整运行，可检查每个基准两fork各三次测量。源码结果检查发生在Setup阶段，工作集1024、单线程、简单值，不能推断生产多线程/尾延迟/所有硬件。
