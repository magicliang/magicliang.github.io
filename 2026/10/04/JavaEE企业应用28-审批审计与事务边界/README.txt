28 | 审批审计与原子回滚实验卡（无二进制素材）

现有业务可写采购申请，但没有 approval_audit 表、ActorDirectory 或审批审计服务。本文 CREATE TABLE 的 (tenant_id,request_id) 外键必须先由 26 的 (tenant_id,id) 唯一迁移支撑；直接在原库执行会失败。全部迁移和测试 NOT_RUN。

前置：24/25 的身份与对象授权；独立 javaee_lab；两张合成 SUBMITTED 申请及受限 actor。正常：条件审批 UPDATE 1 行，成功审计 INSERT，受管事务提交后第三连接同时见 APPROVED/version+1 与一条事件。失败：另一申请的审计 INSERT 违反 NOT NULL，事务应整体回滚；跨租户或旧版本不能写 APPROVED。需要持久拒绝尝试时用独立受管事务记 DENIED，不冒充成功审批。

正文 psql SQL 仅验证数据库原子性，不验证 Jakarta Transactions 的两个 DAO 确实共用受管事务。保存两层证据：SQLSTATE/第三连接终态 + 部署版本/WAR/受管调用与异常链；脱敏，不保存原始 Cookie/口令/敏感报价。NOT_RUN。
