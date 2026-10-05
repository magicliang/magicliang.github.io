# 08 研究卡：迁移与 PostgreSQL 集成测试

- 来源：Persistence 3.2 §8.2.1.11、§9.4；PostgreSQL 16 的 `ALTER TABLE`、`CREATE INDEX`、约束与 `psql` 手册；Hibernate ORM 7.1 Schema generation。
- 工程输入：`examples/jpa/db/migrations/01-init.sql`、`examples/jpa/src/main/resources/META-INF/persistence.xml`、`examples/jpa/src/test/java/blog/jpa/ProcurementJpaTest.java`。只对专用、可丢弃的 `jpa_lab` 库执行文章所列命令；不能拿其他系列或已有业务数据的库重置测试。
- 正常断言：脚本退出零，目录结构有 `version`、订单唯一外键和 CHECK；工程测试退出零并核对独立上下文读到的持久终态。失败断言：漏迁移/缺版本导致测试非零，非法状态 INSERT 因 CHECK 非零且无新增行；保留完整异常链，不能把 `IF NOT EXISTS` 当旧库迁移。
- 旧库实验缺口：需要旧版本结构 fixture、版本化增量迁移、旧数据回填与验证 SQL，均未在现有工程实现。旧库不能用 01 初始化脚本替代。并发双订单/租户所有读取路径也没有独立覆盖。
- 证据清单：源码提交 SHA（未提交则文件哈希）、PostgreSQL/Provider/驱动版本、连接目标（脱敏）、命令与退出码、原始输出、断言、数据库终态、必要时实测 SQL/耗时；不预填任何数值。
- 证据与状态：`writing-plans/jpa/verification/20261004T053805Z-pg16-resource-local/RUN.md` 归档 `clean test` 的 6/6 PASS、源码逐文件哈希、退出码和原始测试输出；初始化 SQL 当时退出 0 但 stdout 未归档，不算独立迁移验收。本文筛选命令、缺迁移、坏结构、非法 CHECK 及旧库升级均 NOT_RUN；研究卡不替代缺失实验。
