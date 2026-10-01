# 29 DNS/Service/Policy 对照

专用 kind VM 中固定并确认支持 NetworkPolicy 的插件及源码版本，选定自有 namespace、探针镜像 digest、两只自建 Pod。校验附件后分别发起 Pod IP 直连、Service 域名解析与请求，记录 DNS 答案、EndpointSlice、节点转发实现与每次后端 UID/PID。

```sh
kubectl -n "$OWN_NAMESPACE" get pods,svc,endpointslices -o wide
kubectl -n "$OWN_NAMESPACE" get networkpolicy -o yaml
```

只在自有 namespace 注入一条拒绝策略与允许策略；逐条请求记录 HTTP 状态和抓包，删除自建策略与对象并确认恢复。当前未安装插件/kind，`NOT_RUN`。
