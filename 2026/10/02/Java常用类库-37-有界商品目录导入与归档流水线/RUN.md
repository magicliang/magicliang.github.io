# 第37章：完整流水线实验

Java8源码基线，实测Zulu8u472与Corretto21.0.11。固定依赖沿用examples/java-libraries/pom.xml：Guava33.5.0-jre、CSV1.14.1、Jackson2.20.1、HttpClient5.6.4、Compress1.28.0，无新增依赖。

从仓库根目录运行完整loopback场景：

```sh
cd examples/java-libraries
./mvnw -B -ntp -s .mvn/settings.xml -Dtest=blog.libraries.Chapter37Test test
```

需要允许127.0.0.1临时端口监听。服务不接外部网络，测试结束停止服务器并等待线程池退出。首次Maven运行可能下载依赖。切换JAVA_HOME分别在Java8/21执行；完整原始证据在evidence/37。

附件CatalogPipeline.java与主工程main类逐字节相同，包含全部imports与main。它复用Product.java、Catalog.java以及io包下BoundedIo.java、SafePaths.java、PrivateArchive.java，附件同时提供这些文件。按各文件package声明还原目录，或直接使用示例工程。Chapter37Test.java包含完整HTTP服务夹具和六项测试，不需要另写服务即可复现。

运行独立main时，CLASSPATH应包含target/classes及pom解析出的全部运行依赖；实际测试classpath保存在JUnit XML的java.class.path中。提供一个可信的详情接口，返回200和`{"label":"商品"}`，再执行：

```sh
java -cp "$CLASSPATH" blog.libraries.CatalogPipeline sample.csv \
  http://127.0.0.1:8080/detail /absolute/trusted/output-parent
```

sample.csv见同目录附件；输出父目录必须事先存在且由调用方控制。main打印JSON与ZIP大小，随后关闭Export删除临时目录，不会留下永久发布的归档。测试的outputBudgetsAndStandaloneMainLeaveNoArtifacts真实调用该main，并提供随机端口服务。

运行边界：run借用输入流和HttpClient，不关闭二者；响应/实体/输出流由内部关闭。成功Export由调用方close，失败和取消删除workspace。run接收客户端的超时、重定向和重试政策由调用方配置；main已设置连接/池租借/响应超时并禁用重试和重定向。取消只在协作检查点生效，不中断正在阻塞的read，也不承诺远端撤销或统一端到端期限。

验收覆盖：成功不可变索引/频次/[0,10)查询/真实HTTP/ZIP解开字节一致；非法精度、负数、指数、重复键、ID、列数、表头、空行、非法UTF8；字节/行数预算；中途503、响应超量、重复/尾随JSON、schema与UTF8失败；三个取消点；报告和ZIP输出预算；借入流所有权、HTTP leased=0、目录及服务线程清理。
