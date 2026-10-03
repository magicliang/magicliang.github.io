# 第06篇运行记录

2026-10-03 当前检出版本在专用 PostgreSQL 16.15 / OpenJDK 21.0.12.1 / Hibernate 7.1.36.Final 实跑：2 项 JUnit 测试覆盖 3 场景，0 失败、0 错误、0 跳过；退出码 0。完整实现为 `examples/hibernate-lab/src/test/java/blog/hibernate/Chapter06Test.java`。

从 `examples/hibernate-lab/` 运行 `./mvnw -B -ntp -Dtest=Chapter06Test test`；通过 `HIBERNATE_LAB_JDBC_URL`、`HIBERNATE_LAB_USER`、`HIBERNATE_LAB_PASSWORD` 提供专用库连接，密码不入库。

云端 PostgreSQL 16.15 记录为 `examples/hibernate-lab/evidence/06/20261003T031711Z-pg16-first/` 的 `command.txt`、`environment.txt`、`test.stdout.txt`、`exit-code.txt`、JUnit XML 和另起连接执行的 `db-final.txt`。主仓还保留此前 PostgreSQL 17.6 原始输出，同步后另跑 `examples/hibernate-lab/evidence/00-12/20261003-pg17-synced-local/`，未增强累计 50/50。各轮环境和终态分别保留，临时路径描述不代替仓库原始证据。

| 场景 | 二元可观测结果 | 原始仓库证据 |
|---|---|---|
| merge 后只改输入 | 输入 99.00、返回仍 20.00、身份断言通过；新连接最终 20.00 | `test.stdout.txt`、JUnit XML、`db-final.txt` |
| merge 后只改返回 | 输入仍 20.00、返回 30.00；新连接最终 30.00 | 同上 |
| 两个脱管副本同 id 级联 | merge 调用内 `IllegalStateException` 含 `Multiple representations`；回滚后新连接最终 10.00 | 同上 |

测试内的新 JDBC 连接显式使用 READ COMMITTED，`db-final.txt` 是测试后另一条 PostgreSQL 连接的读取。冲突是 ORM 侧异常而非数据库异常，不能填充 SQLState。StatementInspector 的语句文本不能单独证明提交成功。

上游 Gradle 测试、allow/log 覆盖策略及正文练习均未运行，状态为 `NOT_RUN`。页面和浏览器验收以本批新生成的记录为准，不由测试通过代替。
