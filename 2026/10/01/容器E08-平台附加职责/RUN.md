# E08 声明与执行面

独立 kind VM 固定 Kubernetes、CNI、控制器/策略实现版本，校验 probe-app 包并构建固定 digest。只在自有 namespace 分别创建标准 Deployment/Service 与一种选定的策略扩展。保存 controller 对象/事件、Pod UID/容器 ID/PID、真实请求成功/拒绝和控制器停止时对比，再清理只属于实验的对象。不能将任意 CRD 的创建成功视为数据面生效；当前无 kind/控制器，完整案例 `NOT_RUN`。
