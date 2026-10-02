# 22 netns → veth → HTTP

已有真实但**仅限 namespace 视图**的只读实验：环境见 00，原始命令、时间、inode、退出码和清理见 `netns-raw.txt`。只有 `LAB_VERIFIED（局部）`，不能把它写成 veth 通信已通过。

```sh
readlink /proc/self/ns/net
unshare -Ur -n sh -c 'readlink /proc/self/ns/net; cat /proc/net/dev'
readlink /proc/self/ns/net
```

三步返回 0，子 namespace 有不同 inode，仅有 lo，退出后原 inode 不变。这**不等于** veth 实验完成。下述操作需要**独占一次性 Linux VM** 的 `iproute2`、Python 3、curl、可选 tcpdump、CAP_NET_ADMIN；不在当前共享云端运行（无 `ip`，且不得修改共享宿主网络）。命名前缀仅供一次性 VM 使用，开始前确认 `containers-22-a/b` 不存在，冲突时停止，不能删已有对象。自建 `/tmp/containers-22-state` 与探针进程均需要自行核对。提取本篇附件并核对 SHA，使用 VM 内 Python 直接运行同一 `probe_app.py`，不宣称这是容器运行。

输入、基线和创建（每行保存完整 stdout/stderr、起止 UTC 与退出码；失败时仍执行本文件清理段）：

```sh
date -u +%FT%TZ
uname -a
ip -V
python3 --version
sha256sum -c CHECKSUMS.sha256
mkdir -p lab-src
tar -xzf probe-bundle.tar.gz -C lab-src
ip netns list
ip -br link
ip netns add containers-22-a
ip netns add containers-22-b
ip -n containers-22-a link add veth22a type veth peer name veth22b
ip -n containers-22-a link set veth22b netns containers-22-b
ip -n containers-22-a link show
ip -n containers-22-b link show
ip netns exec containers-22-a readlink /proc/self/ns/net
ip netns exec containers-22-b readlink /proc/self/ns/net
ip netns exec containers-22-a curl -i --max-time 2 http://192.0.2.2:18080/health
echo "before_addr_rc=$?"
ip -n containers-22-a route get 192.0.2.2
```

仅为自建 veth 在 netns 内配文档地址；从 A 检查直到第一次成功，若成功条件早于预期，查实际路由与进程 namespace，不改写真实输出：

```sh
ip -n containers-22-a addr add 192.0.2.1/30 dev veth22a
ip -n containers-22-b addr add 192.0.2.2/30 dev veth22b
ip -n containers-22-a link set lo up
ip -n containers-22-b link set lo up
ip -n containers-22-a link set veth22a up
ip -n containers-22-b link set veth22b up
ip -n containers-22-a addr show
ip -n containers-22-b addr show
ip -n containers-22-a route
ip -n containers-22-b route
ip -n containers-22-a route get 192.0.2.2
ip netns exec containers-22-b python3 -B lab-src/probe_app.py --host 0.0.0.0 --port 18080 --state-dir /tmp/containers-22-state &
SERVER_PID=$!
ip netns exec containers-22-a curl -i --max-time 2 http://192.0.2.2:18080/health
echo "connected_rc=$?"
ip -n containers-22-a neigh show
ip -n containers-22-b neigh show
```

抓包仅在本篇 veth 端点上，**可选**：用两个终端分别 `ip netns exec containers-22-a timeout 5 tcpdump -ni veth22a -c 30`、`ip netns exec containers-22-b timeout 5 tcpdump -ni veth22b -c 30`，在运行期间重试 A 的 HTTP 请求。保存 tcpdump 的版本、过滤条件、起止时间、每侧原始输出和退出码；缺工具则抓包 `NOT_RUN`，不能拿 `ip neigh` 冒充双端包证据。

先停掉且 `wait` 上面记录的本篇 `SERVER_PID`，只改应用绑定地址再复用同一地址/路由；回环请求在 B、本机 veth IP 请求在 A，逐项对照：

```sh
kill -TERM "$SERVER_PID"
wait "$SERVER_PID"
ip netns exec containers-22-b python3 -B lab-src/probe_app.py --host 127.0.0.1 --port 18080 --state-dir /tmp/containers-22-state &
SERVER_PID=$!
ip netns exec containers-22-b curl -i --max-time 2 http://127.0.0.1:18080/health
echo "local_rc=$?"
ip netns exec containers-22-a curl -i --max-time 2 http://192.0.2.2:18080/health
echo "remote_rc=$?"
kill -TERM "$SERVER_PID"
wait "$SERVER_PID"
ip netns pids containers-22-a
ip netns pids containers-22-b
ip netns del containers-22-a
ip netns del containers-22-b
ip netns list
ip -br link
```

若后台探针启动失败，`SERVER_PID` 只对应本次 shell 保存的值；不要用 `pkill python` 清理整机进程。删 namespace 前先用 `ip netns pids` 核对只含本篇创建的进程，并结束本篇的抓包；如权限或步骤失败导致残留，仅对这次唯一名称操作，保留返回码并从 VM 管理控制台复核。清理验证需比对实验前后同名 netns/接口不存在，宿主其他接口与默认网络不变。当前云端不能执行上述网络实验，完整正反例继续 `NOT_RUN`。
