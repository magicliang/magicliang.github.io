# 24 CNI 调用与清理

状态：`NOT_RUN`（云端无 `ip`、CNI 二进制、独占 VM）。**只在一次性独占 Linux VM** 操作本篇创建的 `containers-24-a/b/bad` network namespace、`cni24br0`、`/tmp/containers-24-ipam`，不要触碰节点现有 CNI 配置或 Pod；VM 管理员需提供操作 netns/bridge 的权限和恢复入口。可从[上游 plugins v1.7.1 发布页](https://github.com/containernetworking/plugins/releases/tag/v1.7.1)获取与 VM 架构匹配的归档并按发布方的校验材料核对，或在隔离 VM 从该 tag 源码构建；仅把得到的 `bridge`/`host-local` 放到本篇专用目录并记录二进制 SHA-256，不借用系统生产目录。本文引用 libcni `v1.3.1` 为源码阅读定点，直接执行二进制**不等于**已运行 libcni/CRI。`cni24-bridge.conf` 固定 CNI spec 配置版本 `1.0.0`，`cni24-bad-ipam.conf` 限故障实验，两个文件须通过 `CNI_CHECKSUMS.sha256` 校验。

以下是补跑入口（工作目录是**本篇素材目录**；用 VM 本地可信插件路径设置 `CNI_BIN_DIR`，不是随便指向节点生产插件目录）；每条命令保留起止 UTC、完整输入/环境/标准输入、插件 stdout/stderr、退出码、预期与实际差异。`ADD` 的 stdout 原样保存到临时 JSON 文件，stderr 和返回码另保存；后续只从实际文件读 IP，不把示意网段值当已分配结果。任何中途失败也要按本篇唯一 ID/对象清理，失败原因不得强行改写为已成功。

```sh
date -u +%FT%TZ
uname -a
ip -V
: "${CNI_BIN_DIR:?point to trusted v1.7.1 bridge and host-local directory}"
test -x "$CNI_BIN_DIR/bridge"
test -x "$CNI_BIN_DIR/host-local"
sha256sum "$CNI_BIN_DIR/bridge" "$CNI_BIN_DIR/host-local"
sha256sum -c CNI_CHECKSUMS.sha256
sha256sum -c CHECKSUMS.sha256
ip netns list
ip -br link
test ! -e /var/run/netns/containers-24-a
test ! -e /var/run/netns/containers-24-b
test ! -e /var/run/netns/containers-24-bad
test ! -e /tmp/containers-24-ipam
ip netns add containers-24-a
ip netns add containers-24-b
ip netns add containers-24-bad
CNI_COMMAND=VERSION CNI_PATH="$CNI_BIN_DIR" "$CNI_BIN_DIR/bridge" < cni24-bridge.conf
CNI_COMMAND=VERSION CNI_PATH="$CNI_BIN_DIR" "$CNI_BIN_DIR/host-local" < cni24-bridge.conf
```

同一 VM shell 内先定义唯一直接调用入口，`CNI_NETNS` 指的是 `ip netns add` 创建的 bind-mount 句柄路径，`CNI_CONTAINERID` 与 `CNI_IFNAME` 对本轮固定；接口不带壳层假设：

```sh
run_cni() {
  CNI_COMMAND="$1" CNI_CONTAINERID="$2" CNI_NETNS="$3" CNI_IFNAME=eth0 CNI_PATH="$CNI_BIN_DIR" "$CNI_BIN_DIR/bridge" < "$4"
}
NS_A=/var/run/netns/containers-24-a
NS_B=/var/run/netns/containers-24-b
NS_BAD=/var/run/netns/containers-24-bad
run_cni ADD containers-24-a "$NS_A" cni24-bridge.conf > add-a.json
echo "add_a_rc=$?"
run_cni ADD containers-24-b "$NS_B" cni24-bridge.conf > add-b.json
echo "add_b_rc=$?"
python3 -m json.tool add-a.json
python3 -m json.tool add-b.json
ip -n containers-24-a addr
ip -n containers-24-b addr
ip -n containers-24-a route
ip -n containers-24-b route
ip link show cni24br0
ip -n containers-24-a link show eth0
ip -n containers-24-b link show eth0
find /tmp/containers-24-ipam -maxdepth 2 -type f -print
```

直接调用所选 `bridge v1.7.1` 的 `CHECK` **需要**上次 ADD 的真实 `prevResult`。下面生成本次临时文件，不覆盖已校验的配置；如果 `ADD` 未成功，不制造 `prevResult`，CHECK 维持 `NOT_RUN` 并先清理。B 实际 IP 要从 ADD 输出解析，不可写死第二个地址：

```sh
python3 -c 'import json,sys; conf=json.load(open(sys.argv[1])); conf["prevResult"]=json.load(open(sys.argv[2])); print(json.dumps(conf))' cni24-bridge.conf add-a.json > check-a.json
python3 -c 'import json,sys; conf=json.load(open(sys.argv[1])); conf["prevResult"]=json.load(open(sys.argv[2])); print(json.dumps(conf))' cni24-bridge.conf add-b.json > check-b.json
sha256sum check-a.json check-b.json
run_cni CHECK containers-24-a "$NS_A" check-a.json
echo "check_a_rc=$?"
run_cni CHECK containers-24-b "$NS_B" check-b.json
echo "check_b_rc=$?"
```

请求验证只使用附件内的标准库探针：校验归档后提取，在 B 的 netns 中以 `0.0.0.0` 监听，自 A 访问上轮实际分配的 B IP；`ip netns exec` 不会凭空创建 PID/mount 隔离，不称这些进程为 Docker 容器。命令有上限，用 `kill`/`wait` 只处理本篇记录的后台 PID：

```sh
mkdir -p lab-src
tar -xzf probe-bundle.tar.gz -C lab-src
IP_B=$(python3 -c 'import ipaddress,json; d=json.load(open("add-b.json")); print(ipaddress.ip_interface(d["ips"][0]["address"]).ip)')
test -n "$IP_B"
ip netns exec containers-24-b python3 -B lab-src/probe_app.py --host 0.0.0.0 --port 18080 --state-dir /tmp/containers-24-state &
SERVER_PID=$!
ip netns exec containers-24-a python3 -c 'import sys,urllib.request; print(urllib.request.urlopen("http://"+sys.argv[1]+":18080/health",timeout=2).status)' "$IP_B"
echo "http_rc=$?"
kill -TERM "$SERVER_PID"
wait "$SERVER_PID"
```

异常输入**仅**针对第三个自建 netns，在配置副本中把 IPAM 指向不存在的实验插件；失败点与残留以实测为准。先查设备/租约，再尝试以相同 ID 和正确配置 DEL；不要先删 netns 后追租约。重复 ADD/CHECK/DEL 的边界须在该 VM 的自建 ID 上另记原始输出，不要对生产 Pod 执行。恢复与清理的命令如下：

```sh
run_cni ADD containers-24-bad "$NS_BAD" cni24-bad-ipam.conf > add-bad.json
echo "bad_add_rc=$?"
ip -n containers-24-bad link show
find /tmp/containers-24-ipam -maxdepth 2 -type f -print
run_cni DEL containers-24-bad "$NS_BAD" cni24-bridge.conf
echo "bad_cleanup_rc=$?"
run_cni DEL containers-24-b "$NS_B" cni24-bridge.conf
echo "del_b_rc=$?"
run_cni DEL containers-24-a "$NS_A" cni24-bridge.conf
echo "del_a_rc=$?"
find /tmp/containers-24-ipam -maxdepth 2 -type f -print
ip netns pids containers-24-a
ip netns pids containers-24-b
ip netns pids containers-24-bad
ip netns del containers-24-a
ip netns del containers-24-b
ip netns del containers-24-bad
ip netns list
ip link show cni24br0
```

若 `ip link show cni24br0` 表明桥还在，先确认它由本篇创建、没有别的端口/使用者，再仅在独占 VM 用 `ip link delete cni24br0` 清理；专用 IPAM 目录只在确认没有其他文件后 `rmdir`。`find` 不可因为目录不存在而默认为“释放成功”：保存返回码与网络对象的前后快照。当前本云端只对 JSON 格式及 SHA 做了 `STATIC_CHECKED`，ADD/CHECK/DEL、IPAM 分配和失败回滚全部 `NOT_RUN`；二进制实际 SHA、VM PID/netns inode/IP 与清理结果都待现场填写。
