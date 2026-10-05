00 研究卡与复跑记录模板（2026-10-04）

事实入口（本地已有文件，GitLab master 路径须在推送后核验）：
examples/javaee-enterprise/pom.xml
examples/javaee-enterprise/webapp/pom.xml
examples/javaee-enterprise/webapp/src/main/java/blog/javaee/web/RestApplication.java
examples/javaee-enterprise/webapp/src/main/java/blog/javaee/web/HealthResource.java
examples/javaee-enterprise/domain/src/test/java/blog/javaee/domain/ProcurementRulesTest.java
examples/javaee-enterprise/deploy/server.xml
examples/javaee-enterprise/scenarios/00-health.sh

规格入口：Jakarta EE Platform 11.0、Web Profile 11.0、Core Profile 11.0、RESTful Web Services 4.0；Java SE 21 javax.sql。以上提供规范与 API 对照，不是本地容器实验结果。

正常路径：限定范围内有证据。写作计划目录 writing-plans/javaee-enterprise/verification/20261004T061900Z-pg16-foundation/ 下的 build-3.stdout.txt 记录 clean verify 全部 reactor SUCCESS，procurement-domain Tests run: 1, Failures: 0, Errors: 0，且 WAR 打包。server-final.stdout.txt 记录 Open Liberty 26.0.0.5 / Java 21.0.12.1 启动、/procurement/ 应用就绪；health.headers.txt 为 HTTP/1.1 200 OK，health.body.txt 为 ready，health-exit-code.txt 为 0。只证明最小 WAR 构建、容器启动及该健康路由响应；不证明采购事务/鉴权/数据库连接/通知。
失败路径：NOT_RUN（未找到错误端口、错误路径及恢复请求的原始证据）。

已存证据中 base-commit.txt 为 bdb589f063c62efdfa124002d29b5417b62946c8；不能仅凭该文件断言未提交工作树与生成 WAR 完全一致。复跑前填写：当前代码 SHA=待采集；JDK/Maven/运行时/OS=待核对；WAR SHA-256=待采集；运行起止时间=待采集；本地隔离数据库=javaee_lab（须确认实际目标）；端口/脱敏配置=待采集。
步骤：从工程目录执行 ../hibernate-lab/mvnw -B -ntp -f "$PWD/pom.xml" clean verify；检查 WAR；按工程 README 启动隔离服务器；设置 JAVAEE_PORT 并执行 bash scenarios/00-health.sh。负向测试改为无监听端口调用脚本，再恢复端口重测。
后续归档：完整命令、退出码、包摘要、脱敏的服务器部署日志、curl 状态/响应体、故障与恢复时间；不得保存密码。已有正常结果见上述原始文件；负向预期为脚本非零，实际结果=待采集，不填预设日志或编造的 HTTP 状态。
边界：健康结果不检查采购业务、数据库连接、租户鉴权或通知。
