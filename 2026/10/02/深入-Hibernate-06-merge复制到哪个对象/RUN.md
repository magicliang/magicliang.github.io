# 第06篇运行记录

2026-10-02 本地执行：LAB_VERIFIED。PostgreSQL17.6 / JDK21.0.11 / Hibernate7.1.36.Final，2项JUnit测试覆盖3场景，0失败、0错误、0跳过；退出码0。完整实现位于 examples/hibernate-lab/src/test/java/blog/hibernate/Chapter06Test.java。

从 examples/hibernate-lab 目录运行 `./mvnw -B -ntp -Dtest=Chapter06Test test`，需要 HIBERNATE_LAB_JDBC_URL、HIBERNATE_LAB_USER、HIBERNATE_LAB_PASSWORD 指向隔离 PostgreSQL。

此次本机使用离线依赖缓存与仅含Maven Central的临时settings，精确命令：`source /private/tmp/hibernate-runtime-pg17/env.sh && ./mvnw -o -s /private/tmp/hibernate-maven-central.xml -Dmaven.repo.local=/private/tmp/hibernate-m2 -B -ntp -Dtest=Chapter06Test test`。临时绝对路径仅描述这次本机执行；迁移机器后使用标准命令和当地环境变量。

| 场景 | 二元可观测结果 | 原始仓库证据 |
|---|---|---|
| merge后只改输入 | id9输入99.00、返回仍20.00、contains身份断言通过；新连接最终20.00 | examples/hibernate-lab/evidence/06/20261002-pg17/test.txt；surefire.xml |
| merge后只改返回 | id10输入仍20.00、返回30.00；新连接最终30.00 | 同上 |
| 两个脱管副本同id级联 | merge调用内IllegalStateException含Multiple representations；新连接最终10.00 | 同上；observables.txt |

测试内的新JDBC连接明确设置READ_COMMITTED。图冲突订单id为7461045945920866618，已回滚金额修改；数据库终态由测试内SQL查询断言。SQL及bind原始日志保留在test.txt，观察器异常并非数据库异常，不能伪造SQLState。

编译、来源核对、写作扫描和全部证据索引在 examples/hibernate-lab/evidence/06/20261002-pg17/README.md。Hexo生成和浏览器视觉验收由父任务执行，此记录不宣称已完成这两项。

上游Gradle测试、allow/log覆盖策略及正文练习均未运行，状态NOT_RUN。
