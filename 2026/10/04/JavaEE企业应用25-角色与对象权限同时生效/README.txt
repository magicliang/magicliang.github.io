25 | 授权矩阵实验卡（无二进制素材）

已存在：JdbcRequestStore.transition 使用 id、tenant_id、status、version 条件更新；/api/lab/requests/{id}/approve 不做可信认证、角色或额度检查。它是隔离演示，不能当授权通过证据。

前置：实现 24 的身份与可信租户、受管容器角色映射、申请 created_by、approver_grant 迁移、正式 /api/requests/{id}/approve；冻结额度币种、调岗撤销生效顺序及 Cookie 方案所需 CSRF。新增部分均 NOT_RUN。

按主体/角色/租户/额度/状态/版本建表：匿名、BUYER、合法 APPROVER、他租户 APPROVER、超额度 APPROVER、旧版本 APPROVER。正常只允许同租户、额度内、待批且版本匹配的审批；拒绝后从独立连接查申请版本与审计，不可只记 403/404/409。并发调岗需共同锁授权行或另定可验证生效顺序。

记录：身份来源、角色映射、请求 ID、受管调用轨迹、UPDATE 行数、拒绝原因码、数据库最终行及退出码。正文 HTTP 示例是实施后接口合同，NOT_RUN。
