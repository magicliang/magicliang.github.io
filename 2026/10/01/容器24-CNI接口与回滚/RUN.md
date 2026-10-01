# 24 CNI 调用与清理

专用 Linux VM 固定 CNI 规范与 bridge/IPAM 插件具体版本、二进制 SHA-256，并将调用接口、实现源码 tag/commit 写入 VERSIONS。只对两个自建 netns 与自建 IPAM 配置执行 ADD/CHECK/DEL，不得借用 Kubernetes 现有 Pod 的 netns。输入包括 `CNI_COMMAND`、`CNI_CONTAINERID`、`CNI_NETNS`、`CNI_IFNAME`、`CNI_PATH` 与标准输入 JSON。每一次保存完整环境变量、配置字节、插件 stdout/stderr、返回码及 `ip` 对象；DEL 后检查设备、地址租约全部释放。

`probe_app.py` 仅用来确认 ADD 后真实 HTTP 路径。失败案例只修改自建插件链副本并按相同 ID 重试。当前无插件或 `ip`，且源码版本未选定：所有 CNI 调用、CHECK/DEL、失败回收 `NOT_RUN`，此目录的源码包不是插件实现。
