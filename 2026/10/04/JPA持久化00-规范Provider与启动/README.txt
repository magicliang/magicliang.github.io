# 00 研究卡：启动链

- 规范：Jakarta Persistence 3.2 §3.2、§3.3.2/3.3.4、§7.2–7.5、§8.2、§9.2；Provider Hibernate ORM 7.1.36.Final，数据库 PostgreSQL 16。
- 实际代码：[累计工程源码树](https://gitlab.alibaba-inc.com/liangchuan.lc/my-blogs/-/tree/master/examples/jpa/)；[启动辅助类](https://gitlab.alibaba-inc.com/liangchuan.lc/my-blogs/-/blob/master/examples/jpa/src/test/java/blog/jpa/DatabaseSupport.java)；[JUnit 入口](https://gitlab.alibaba-inc.com/liangchuan.lc/my-blogs/-/blob/master/examples/jpa/src/test/java/blog/jpa/ProcurementJpaTest.java)。
- 输入：独立 `jpa_lab`，`db/migrations/01-init.sql`，Java 21.0.12.1、Maven Wrapper 3.9.9、pgJDBC 42.7.7。已归档 `clean test` 6/6、退出码 0，见 `writing-plans/jpa/verification/20261004T053805Z-pg16-resource-local/RUN.md` 及原始 stdout、代码 SHA。
- 00 范围内已验证：`lifecycleAndServerCalculatedTotal` 的 persist/find、提交/clear 后重载、金额与明细断言。迁移命令实际退出 0，但原始 stdout 未归档，不能认作独立迁移验收。
- NOT_RUN：单方法筛选命令、错驱动类、错 JDBC URL、坏依赖版本探针及其异常链。构建失败不能当数据库失败；JTA、第二 Provider 未覆盖。
