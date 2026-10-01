# 25 两台 VM 双端抓包

至少两台独立 Linux VM、专用网络地址、固定插件/内核版本、宿主控制台。先校验探针包，再记录双方接口 MTU、路由、封装端点、Pod IP 与连接端口。仅在自建虚拟网络内分别实现直接路由与一种 VXLAN 路径；双端抓包并用有上限的请求体比较小包、大包与 ICMP/PMTU。

```sh
ip -d link show
ip route show
tcpdump -i "$OWN_LAB_IFACE" -w "$OWN_LAB_CAPTURE" -c 200
```

预先填 `OWN_LAB_IFACE` 为实验接口，`OWN_LAB_CAPTURE` 为自建目录文件；capture 最多 200 包。故障注入只在自建 VXLAN 接口改变 MTU，测试后恢复、删自有路由/接口并在两台 VM 核对清理。当前只有单一共享云端，无 `ip`、第二 VM，完整实验 `NOT_RUN`。
