# 22 netns → veth → HTTP

已运行的只读实验（环境见 00，原始数据见 `netns-raw.txt`）：

```sh
readlink /proc/self/ns/net
unshare -Ur -n sh -c 'readlink /proc/self/ns/net; cat /proc/net/dev'
readlink /proc/self/ns/net
```

三步返回 0，子 namespace 有不同 inode，仅有 lo，退出后原 inode 不变。这**不等于** veth 实验完成。补跑仅专用 VM 的私有网络实验，用 `ip netns add containers-22-a` 与 `containers-22-b`、`ip link add ... type veth peer name ...`，将两端放入自建 netns，逐步配置地址/路由/lo 并分别请求同一 `probe_app.py`；记录 `ip -n ... link/addr/route` 与双端抓包。只删自己创建的 netns 与 veth，检查 `ip netns list` 和设备列表无残留；共享云端无 `ip`，完整正反例 `NOT_RUN`。
