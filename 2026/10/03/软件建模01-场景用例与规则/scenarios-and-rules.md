# 01：场景、用例与规则

材料边界：合成教学案例；没有访谈。业务约定来自 00 的 three-models.md 和当前 README.md。实现映射是核对结果，不是现实规则的权威来源。时间均为 2026-10-03 UTC，半开区间，小时粒度仅用于示例。

## 用例 UC01：取得指定设备在指定租期的预留

主要参与者：租赁经办角色。系统边界：单个 RentalDesk 实例。触发：提交设备 E1、租期和请求 ID。前置：提供完整请求；不把“设备无冲突”列为前置，以免排除异常场景。成功后置：新增有效预留和成功回执；失败保证：不占用新资源，合法但冲突的请求保留拒绝回执。输入不合法则抛出异常。

正常步骤：提交 → 判断请求身份与租期 → 判断占用 → 登记预留与回执 → 返回结果。这是外部行为草案；不承诺并发原子性或持久化事务。

## 来源目录

- A0：models/00/three-models.md 教学需求及 S00-01 至 S00-07、C00-01。
- A1：README.md 公开 API 与区间、请求回执、取消契约（本系列自行设定）。
- M1：Jacobson/Cockburn, Use-Case Foundation v1.1，p1、p4，https://alistaircockburn.com/Use%20Case%20Foundation.pdf 。方法来源，不提供租赁规则。
- M2：Business Rules Group, Business Rules Manifesto v2.0，§§2–4，https://www.businessrulesgroup.org/brmanifesto/BRManifesto.pdf 。表达原则，不提供租赁规则。

## 规则追踪

| ID/类别 | 约定与来源 | 反例 | 代码位置 | 实验 |
|---|---|---|---|---|
| R1 业务 | 同一设备有效预留不得重叠；A0 教学需求、S00-02 | 已有 E1 [10,12)，再确认 E1 [11,13) | reserve 的 conflict 比较与 Period.overlaps | S02；S04 验证设备限定 |
| R2 业务 | 租期 start < end；A1 | 接受 [10,10) 或 [12,10) | Period 构造器 | S05 |
| R3 业务边界约定 | [start,end)，相邻可预留，暂忽略清洁；A0 S00-03、C00-01；A1 | 把 E1 [12,13) 判为与 [10,12) 冲突 | Period.overlaps 严格小于 | S03 |
| R4 业务 | 取消移除有效预留；A0 S00-06；A1 | 取消后新 ID 仍因已取消预留而被拒绝 | cancel 删除 bookings | S08 |
| C1 应用契约 | 同 ID 同负载返回原结果，异负载非法；A0 S00-04/05；A1 | 同 ID 换设备成功 | reserve 的 receipts 与 request.equals | S06/S07 |
| C2 应用契约 | 取消不删回执，拒绝结果也保留；A0 S00-06/07；A1 | 取消后旧请求重新占位；资源空闲后旧拒绝变成功 | cancel 与 reserve 回执分支 | S08/S09 |

## 场景索引

| 场景 | 分类 | 输入/前置 | 二元判断 |
|---|---|---|---|
| S01 | 正常 | 空实例，A E1 [10,12) | CONFIRMED |
| S02 | 异常 | 已有 A，B E1 [11,13) | OVERLAP_REJECTED |
| S03 | 边界 | 已有 A，C E1 [12,13) | CONFIRMED |
| S04 | 边界 | 已有 A，D E2 [10,12) | CONFIRMED |
| S05 | 边界 | 等端点、倒置端点 | IllegalArgumentException |
| S06 | 重试 | 原 A 再次提交 | 原 CONFIRMED |
| S07 | 异常 | A 更换设备；随后新 E 与原 A 重叠 | 异常；原预留仍排斥 E |
| S08 | 取消 | 取消 A 两次、重放 A、新 F 同租期 | true、false、CONFIRMED、CONFIRMED |
| S09 | 异常后恢复 | 独立实例中 A 阻挡 B；取消 A；重试 B；新 G | B 仍拒绝，G 确认 |
| S10 | 边界 | 取消拒绝 ID 或未知 ID | false |

## 未决问题

Q1 取消授权：谁可取消他人的预留，租期开始后是否允许？当前 cancel 仅接收 RequestId，无操作者、所有权或截止时刻。不能宣称已实现授权。未来需要参与方/权限策略和拒绝后的不变性断言。

Q2 清洁占用：若结束后需半小时清洁，合同 [10,12) 的资源占用可能为 [10,12:30)。需确认清洁是否所有设备必需、是否可豁免、取消是否释放清洁占用。当前 S03 接受 12 点相邻预留，证明基线不包含该要求；不把新要求偷偷改成 <=。

Q3 回执生命周期：保留多久、跨进程如何识别请求？当前实例内一直保留；重启后不存在。这里仅记录未决项。
