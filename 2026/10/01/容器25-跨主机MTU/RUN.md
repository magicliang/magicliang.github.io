# 25：双 VM 直路由、VXLAN 与 MTU 取证

状态：`NOT_RUN`。当前共享云端没有第二台 VM、`ip` 或抓包能力；以下是**待专用环境执行**的命令，不是实验输出。只在两台独占 Linux VM（A/B）上由有控制台访问权的操作者执行；不要在共享宿主、生产网络、现有 Pod 网段运行。实验用本机 `c25dummy`、`c25vx` 两个新设备，VNI 25025，UDP 端口 4789，独占地址 `10.254.25.1/32`、`10.254.25.2/32` 和 `10.254.26.1/24`、`10.254.26.2/24`；这些只是**示例地址**，若冲突须在两机一致改为实验室获批的独占地址。实验前在两侧记录所选内核、`iproute2`、`tcpdump` 版本及 VM/网络拓扑；先检查安全组允许专用 VTEP 间 UDP 4789 及双向直路由流量。

## 准备与排他检查（两台分别执行）

使用两台 VM 各自的独立空目录，先校验本篇同目录的通用探针包：

```sh
cd /path/to/2026-10-01-容器25-跨主机MTU
sha256sum -c CHECKSUMS.sha256
mkdir -p "$HOME/c25-lab"
cd "$HOME/c25-lab"
date -u +%FT%TZ
uname -a
ip -V
tcpdump --version | head -1
```

在 **A** 设置如下变量；在 **B** 把 `SIDE=A` 换成 `SIDE=B`，并互换实际分配的 underlay 地址。`UNDERLAY_IF` 必须是本次独占实验所用、对端 IP 可直接抵达的接口；这组命令不会改它的地址、MTU 或默认路由。

```sh
export SIDE=A
export UNDERLAY_IF=ens3
export LOCAL_UNDERLAY=192.0.2.11
export PEER_UNDERLAY=192.0.2.12
export LOCAL_DIRECT=10.254.25.1
export PEER_DIRECT=10.254.25.2
export LOCAL_VX=10.254.26.1
export PEER_VX=10.254.26.2
```

示例 `192.0.2.0/24` 仅为文档地址，**不能原样执行**：两台 VM 必须分别填入真实专用 underlay IP、接口及获批的实验网段。B 的直路由与 VX 地址也须分别对调成 `.2`/`.1`。每次启动前都运行以下检查；任何冲突/不可达即停止，不先执行清理命令碰未知设备：

```sh
test "$(id -u)" -eq 0
test "$SIDE" = A -o "$SIDE" = B
test "$LOCAL_UNDERLAY" != 192.0.2.11
test "$PEER_UNDERLAY" != 192.0.2.12
ip -d link show dev "$UNDERLAY_IF"
ip route get "$PEER_UNDERLAY"
! ip link show dev c25dummy >/dev/null 2>&1
! ip link show dev c25vx >/dev/null 2>&1
! ip route show "$PEER_DIRECT/32" | grep -q .
! ip route show 10.254.26.0/24 | grep -q .
ip -br addr show
ip route show
```

以上 `id` 要求已在专用 VM 的 root shell 内；`ip route get` 应显示预期接口与源 IP，否则停止。若 VM 使用不同实验网段，最后一条路由检查也要同步改成实际网段；事先检查防火墙、网络 ACL 和回程路由，**不通过修改共享 sysctl、默认路由或全局 firewall 使实验通过**。若前次中断留下同名设备，先核对当次创建记录，再按末节清理；不要盲删。

## 阶段一：直路由（两侧都设置）

```sh
ip link add c25dummy type dummy
ip addr add "$LOCAL_DIRECT/32" dev c25dummy
ip link set c25dummy up
ip route add "$PEER_DIRECT/32" via "$PEER_UNDERLAY" dev "$UNDERLAY_IF"
ip route get "$PEER_DIRECT" from "$LOCAL_DIRECT"
ip -d link show c25dummy
```

若路由添加失败（对端并非同链路、网关不可用或冲突），先按末节回收本阶段资源，修正实验拓扑再重新开始。直路由的返回路径也须在 B 设置并取证。A/B 各运行一次：

```sh
timeout 10 ping -n -c 3 -W 2 -I "$LOCAL_DIRECT" "$PEER_DIRECT"
ip -s route show "$PEER_DIRECT/32"
```

双端同时抓包：分别在两台 VM 的 `$HOME/c25-lab` 启动下面的有界抓包，然后在 A 重跑上述 `ping`，并在 B 对调方向重跑。`timeout` 的 124 退出码表示抓包到时，不等于通信失败；保留所有真实退出码和 pcap。

```sh
timeout 20 tcpdump -ni "$UNDERLAY_IF" -s 0 -c 200 -w "direct-$SIDE.pcap" "host $PEER_UNDERLAY or host $PEER_DIRECT" &
CAPTURE_PID=$!
wait "$CAPTURE_PID"; printf 'capture_rc=%s\n' "$?"
tcpdump -nn -r "direct-$SIDE.pcap" | head -60
```

不要把 `ping` 作为 probe-app 的 HTTP 成功：若要测真实业务，先在 B 的独占容器/网络命名空间启用包内 `probe_app.py`，记录其绑定地址和端口，在 A 用 `curl --max-time 10` 请求，分别留响应、退出码与双端抓包；当前通用包**没有**替两台 VM 创建该网络命名空间或替应用配置直路由，因此仅凭上面命令不能验收 Pod HTTP 链路。

## 阶段二：VXLAN（两侧分别执行）

先保存直路由结果；VXLAN 使用另一组地址，避免同目的地址命中直路由。两机专用 underlay 互通、双方允许 UDP 4789 后：

```sh
ip link add c25vx type vxlan id 25025 local "$LOCAL_UNDERLAY" remote "$PEER_UNDERLAY" dev "$UNDERLAY_IF" dstport 4789 nolearning
ip addr add "$LOCAL_VX/24" dev c25vx
ip link set c25vx up
ip -d link show c25vx
ip route get "$PEER_VX" from "$LOCAL_VX"
ping -n -c 3 -W 2 -I c25vx "$PEER_VX"; printf 'small_rc=%s\n' "$?"
```

若插件、ARP 或底层 UDP 过滤使小包不通，先检查 `ip neigh show dev c25vx`、两端 UDP 抓包，不要假装进入大包阶段。两端分别启动 `timeout 25 tcpdump -ni "$UNDERLAY_IF" -s 0 -c 200 -w "vx-$SIDE.pcap" "host $PEER_UNDERLAY and (udp port 4789 or icmp)" &`，保存 `$!` 并在结束后 `wait`；另在各 VM 抓 `c25vx` 上的内层 ICMP，文件名为 `inner-$SIDE.pcap`。在 A 和 B 各测 `ping -n -c 3 -W 2 -M do -s 100`、`-s 1400` 和 `-s 1472`，每次用 `timeout 12` 限时并立即记录退出码；IPv4 ICMP `-s` 是**负载字节数**而不是链路帧长度。Linux 可能因接口 MTU 在发送端立即拒绝，也可能发现 PMTU 后改变行为；只有实际的返回码、ICMP 与双端包长才能决定“失败发生在哪一跳”。

故障注入仅在 A 的**本篇自建 VXLAN 设备**上进行：先 `ip -o link show dev c25vx > vx-mtu-before-A.txt`，记下原 MTU，然后执行 `ip link set dev c25vx mtu "$(cat /sys/class/net/$UNDERLAY_IF/mtu)"`，重复同样大小、次数、抓包位置与方向的测试；这仅制造可能超过外层路径 MTU 的条件，**不保证一定会丢包**。如不能稳定复现，记录 `NOT_REPRODUCED` 和原始 pcap，不删除 ICMP 或改动宿主物理接口以追求预设结果。随后在 A 执行 `ip link set dev c25vx mtu <vx-mtu-before-A.txt中记录的整数>`（把尖括号占位符替换为实际数值），重测小包及大包，比较故障前后两端 pcap。

另可在 A 执行 `ip link set c25vx down`，保存单侧故障抓包、超时返回码，再 `ip link set c25vx up` 验证双向恢复；这不是 MTU 故障，不与 MTU 结果混写。

## 记录、清理与状态

每一阶段保存开始/结束 UTC 时间、两侧 `ip -br addr`、`ip route`、`ip -d link show c25vx`、接口 MTU、命令返回码、原始 pcap、`tcpdump -nn -r` 文本、`sha256sum *.pcap`，以及 A/B 对齐后的发包/收包编号。两台 VM 都须采集，同一方向需指出抓包点及是否开启卸载；不要伪造示例输出为证据。`tcpdump` 进程的 20/25 秒上限不足时重新分批抓包，不留后台无限制抓包。

只在确认 `c25dummy`、`c25vx` 是**本次实验创建**且路由确实指向本次 `$PEER_UNDERLAY` 后，两侧分别执行（即使中途失败也按存在的对象选择执行）：

```sh
ip -d link show c25vx
ip route show "$PEER_DIRECT/32"
ip link del c25vx
ip route del "$PEER_DIRECT/32" via "$PEER_UNDERLAY" dev "$UNDERLAY_IF"
ip link del c25dummy
ip link show c25vx
ip link show c25dummy
ip route show "$PEER_DIRECT/32"
```

若其中一项从未创建，跳过对应删除，不能借助 `|| true` 掩盖不明状态；保留创建/清理各次退出码。还要分别确认两端实验地址/路由消失、underlay MTU/默认路由与开始时相同，业务连通未受影响。当前 `LAB_VERIFIED` 仍是 `NOT_RUN`；只有两台 VM 真实执行并保存原始文件后才更新进度。
