# 22 netns → veth → HTTP

已有真实但**仅限 namespace 视图**的只读实验：环境见 00，原始命令、时间、inode、退出码和清理见 `netns-raw.txt`。只有 `LAB_VERIFIED（局部）`，不能把它写成 veth 通信已通过。

```sh
readlink /proc/self/ns/net
unshare -Ur -n sh -c 'readlink /proc/self/ns/net; cat /proc/net/dev'
readlink /proc/self/ns/net
```

三步返回 0，子 namespace 有不同 inode，仅有 lo，退出后原 inode 不变。这**不等于** veth 实验完成。下述操作需要**独占一次性 Linux VM** 的 `iproute2`、Python 3、curl、可选 tcpdump、CAP_NET_ADMIN；不在当前共享云端运行（无 `ip`，且不得修改共享宿主网络）。从本篇同名素材目录执行命令，只在本任务工作树的 `examples/containers/.lab-work/22` 存放本轮源码和状态目录，不在 `/tmp` 展开探针或新建程序。保持以下三个代码块在同一个 root shell 会话运行；任一步失败先记原始输出并按**实际创建的对象**手动清理，不能盲目继续执行后续块。

输入、基线和创建（每行保存完整 stdout/stderr、起止 UTC 与退出码；失败时仍执行本文件清理段）：

```sh
set -eu
test "$(id -u)" -eq 0
date -u +%FT%TZ
uname -a
ip -V
python3 --version
sha256sum -c CHECKSUMS.sha256
OWN_LAB_ROOT="$(git rev-parse --show-toplevel)/examples/containers/.lab-work/22"
mkdir -p "$OWN_LAB_ROOT"
test ! -L "$OWN_LAB_ROOT"
chmod 700 "$OWN_LAB_ROOT"
OWN_WORK=$(mktemp -d "$OWN_LAB_ROOT/round.XXXXXX")
OWN_SUFFIX="${OWN_WORK##*.}"
OWN_NS_A="containers22a-$OWN_SUFFIX"
OWN_NS_B="containers22b-$OWN_SUFFIX"
OWN_VETH_A="v22a$OWN_SUFFIX"
OWN_VETH_B="v22b$OWN_SUFFIX"
OWN_STATE="$OWN_WORK/state"
mkdir -m 700 "$OWN_STATE" "$OWN_WORK/lab-src"
printf 'work=%s ns_a=%s ns_b=%s veth_a=%s veth_b=%s\n' "$OWN_WORK" "$OWN_NS_A" "$OWN_NS_B" "$OWN_VETH_A" "$OWN_VETH_B"
tar -xzf probe-bundle.tar.gz -C "$OWN_WORK/lab-src"
ip netns list
ip -br link
if ip netns list | awk '{print $1}' | grep -Fx "$OWN_NS_A"; then exit 1; fi
if ip netns list | awk '{print $1}' | grep -Fx "$OWN_NS_B"; then exit 1; fi
ip netns add "$OWN_NS_A"
ip netns add "$OWN_NS_B"
ip -n "$OWN_NS_A" link add "$OWN_VETH_A" type veth peer name "$OWN_VETH_B"
ip -n "$OWN_NS_A" link set "$OWN_VETH_B" netns "$OWN_NS_B"
ip -n "$OWN_NS_A" link show
ip -n "$OWN_NS_B" link show
ip netns exec "$OWN_NS_A" readlink /proc/self/ns/net
ip netns exec "$OWN_NS_B" readlink /proc/self/ns/net
if ip netns exec "$OWN_NS_A" curl -i --max-time 2 http://192.0.2.2:18080/health; then echo 'before_addr_rc=0'; else echo "before_addr_rc=$?"; fi
if ip -n "$OWN_NS_A" route get 192.0.2.2; then echo 'before_route_rc=0'; else echo "before_route_rc=$?"; fi
```

仅为自建 veth 在 netns 内配文档地址；从 A 检查直到第一次成功，若成功条件早于预期，查实际路由与进程 namespace，不改写真实输出：

```sh
ip -n "$OWN_NS_A" addr add 192.0.2.1/30 dev "$OWN_VETH_A"
ip -n "$OWN_NS_B" addr add 192.0.2.2/30 dev "$OWN_VETH_B"
ip -n "$OWN_NS_A" link set lo up
ip -n "$OWN_NS_B" link set lo up
ip -n "$OWN_NS_A" link set "$OWN_VETH_A" up
ip -n "$OWN_NS_B" link set "$OWN_VETH_B" up
ip -n "$OWN_NS_A" addr show
ip -n "$OWN_NS_B" addr show
ip -n "$OWN_NS_A" route
ip -n "$OWN_NS_B" route
ip -n "$OWN_NS_A" route get 192.0.2.2
ip netns exec "$OWN_NS_B" python3 -B "$OWN_WORK/lab-src/probe_app.py" --host 0.0.0.0 --port 18080 --state-dir "$OWN_STATE" &
SERVER_PID=$!
if ip netns exec "$OWN_NS_A" curl -i --max-time 2 http://192.0.2.2:18080/health; then echo 'connected_rc=0'; else echo "connected_rc=$?"; fi
ip -n "$OWN_NS_A" neigh show
ip -n "$OWN_NS_B" neigh show
```

抓包仅在本篇 veth 端点上，**可选**：用两个终端分别 `ip netns exec "$OWN_NS_A" timeout 5 tcpdump -ni "$OWN_VETH_A" -c 30`、`ip netns exec "$OWN_NS_B" timeout 5 tcpdump -ni "$OWN_VETH_B" -c 30`，在运行期间重试 A 的 HTTP 请求。保存 tcpdump 的版本、过滤条件、起止时间、每侧原始输出和退出码；缺工具则抓包 `NOT_RUN`，不能拿 `ip neigh` 冒充双端包证据。

先停掉且 `wait` 上面记录的本篇 `SERVER_PID`，只改应用绑定地址再复用同一地址/路由；回环请求在 B、本机 veth IP 请求在 A，逐项对照：

```sh
kill -TERM "$SERVER_PID"
wait "$SERVER_PID"
ip netns exec "$OWN_NS_B" python3 -B "$OWN_WORK/lab-src/probe_app.py" --host 127.0.0.1 --port 18080 --state-dir "$OWN_STATE" &
SERVER_PID=$!
if ip netns exec "$OWN_NS_B" curl -i --max-time 2 http://127.0.0.1:18080/health; then echo 'local_rc=0'; else echo "local_rc=$?"; fi
if ip netns exec "$OWN_NS_A" curl -i --max-time 2 http://192.0.2.2:18080/health; then echo 'remote_rc=0'; else echo "remote_rc=$?"; fi
kill -TERM "$SERVER_PID"
wait "$SERVER_PID"
ip netns pids "$OWN_NS_A"
ip netns pids "$OWN_NS_B"
ip netns del "$OWN_NS_A"
ip netns del "$OWN_NS_B"
ip netns list
ip -br link
```

若后台探针启动失败，`SERVER_PID` 只对应本次 shell 保存的值；不要用 `pkill python` 清理整机进程。删 namespace 前先用 `ip netns pids` 核对只含本篇创建的进程，并结束本篇的抓包；如权限或步骤失败导致残留，仅对这次唯一名称操作，保留返回码并从 VM 管理控制台复核。清理验证需比对实验前后同名 netns/接口不存在，宿主其他接口与默认网络不变，确认后仅删除 `OWN_WORK` 中本轮创建的文件。若任一步失败仍有进程持有该 namespace，先保留输出与路径供排查，不以删除命名句柄当作清理通过。当前云端不能执行上述网络实验，完整正反例继续 `NOT_RUN`。
