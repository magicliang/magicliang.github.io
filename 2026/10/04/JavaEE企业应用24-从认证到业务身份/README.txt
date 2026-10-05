24 | 认证身份实验卡（无二进制素材）

已有工程仅有 /api/lab/requests 和可伪造 X-Lab-Tenant；JAVAEE_DEMO_MODE=true 只适用于 loopback 隔离测试，不是登录保护。源码定位：rg -n 'X-Lab-Tenant|JAVAEE_DEMO_MODE' examples/javaee-enterprise/webapp/src/main/java。

前置：独立 javaee_lab；冻结 Jakarta EE 11/Java 21/Open Liberty 26.0.0.5；先实现 IdentityStore、受管机制、稳定主体 ID、组织映射、TLS 和 /api/requests/me，关闭公网上的教学路径。以上新增功能全部 NOT_RUN。

正常：合成主体 buyer-17 成功认证，再从受管安全上下文读取主体，按可信组织映射查询申请；保存脱敏 HTTP 状态、主体 ID、最终 SQL 归属。失败：匿名、错误口令、禁用账户、撤销组织关联、旧会话重放，分别记录拒绝发生于认证还是业务映射层；日志不得包含口令或 Cookie。Basic 与 Cookie 方案分开测试，不以关浏览器代表注销。

记录：实际版本与 WAR SHA、配置摘要、测试账户（脱敏）、命令退出码、认证挑战、Cookie ID 的不可逆比较、组织关联变更时刻、数据库终态。站点正文新增的 curl 是实施后合同，当前 URL 不存在，NOT_RUN。
