# 23 端口与解析的三条路径

状态：`NOT_RUN`；共享云端缺 Docker/`ip`/专用 VM。**仅独占 Linux 实验 VM** 用自建 bridge 和三个自建容器，固定 Docker/libnetwork、iproute2、kernel、日志驱动与本次镜像实际 ID。从同名素材目录校验附件；每一轮镜像标签、网络、容器均须唯一，只在本任务工作树的 `.lab-work/23` 解压源码，不改共享网络、全局 DNS 或宿主默认防火墙。下列块在同一个 VM shell 执行；任一步失败记录其创建的对象，先核查身份再只清理这轮资源，不执行后续测试命令。命令逐条保存开始结束 UTC、原始 stdout/stderr 与退出码，不把配置表充作抓包。

```sh
set -eu
date -u +%FT%TZ
uname -a
docker version
docker info --format '{{.Driver}} {{json .SecurityOptions}}'
ip -V
sha256sum -c CHECKSUMS.sha256
OWN_LAB_ROOT="$(git rev-parse --show-toplevel)/examples/containers/.lab-work/23"
mkdir -p "$OWN_LAB_ROOT"
test ! -L "$OWN_LAB_ROOT"
chmod 700 "$OWN_LAB_ROOT"
OWN_WORK=$(mktemp -d "$OWN_LAB_ROOT/round.XXXXXX")
OWN_SUFFIX="${OWN_WORK##*.}"
OWN_NET="containers-net-23-$OWN_SUFFIX"
OWN_A="containers-probe-23-a-$OWN_SUFFIX"
OWN_B="containers-probe-23-b-$OWN_SUFFIX"
OWN_B_LOCAL="containers-probe-23-local-$OWN_SUFFIX"
OWN_TAG="containers-probe:23-$OWN_SUFFIX"
printf 'work=%s net=%s a=%s b=%s local=%s image=%s\n' "$OWN_WORK" "$OWN_NET" "$OWN_A" "$OWN_B" "$OWN_B_LOCAL" "$OWN_TAG"
mkdir -m 700 "$OWN_WORK/lab-src"
tar -xzf probe-bundle.tar.gz -C "$OWN_WORK/lab-src"
docker build -f "$OWN_WORK/lab-src/Dockerfile.multi" -t "$OWN_TAG" "$OWN_WORK/lab-src"
docker image inspect "$OWN_TAG" --format '{{.Id}} {{json .RepoDigests}}'
docker network ls
docker network create --driver bridge "$OWN_NET"
OWN_B_ID=$(docker run -d --name "$OWN_B" --network "$OWN_NET" -p 127.0.0.1::18080 "$OWN_TAG")
OWN_A_ID=$(docker run -d --name "$OWN_A" --network "$OWN_NET" "$OWN_TAG")
docker network inspect "$OWN_NET"
docker inspect "$OWN_B_ID" --format '{{.Id}} {{.State.Pid}} {{json .NetworkSettings.Networks}} {{json .HostConfig.PortBindings}}'
docker inspect "$OWN_A_ID" --format '{{.Id}} {{.State.Pid}} {{json .NetworkSettings.Networks}}'
SERVER_IP=$(docker inspect "$OWN_B_ID" --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
test -n "$SERVER_IP"
PUBLISHED_PORT=$(docker port "$OWN_B_ID" 18080/tcp | awk -F: '$1 == "127.0.0.1" {print $2}')
test -n "$PUBLISHED_PORT"
printf 'published_port=%s\n' "$PUBLISHED_PORT"
docker exec "$OWN_A_ID" python3 -c 'import sys,urllib.request; print(urllib.request.urlopen("http://"+sys.argv[1]+":18080/identity",timeout=2).read().decode())' "$SERVER_IP"
echo "direct_rc=$?"
curl -i --max-time 2 "http://127.0.0.1:$PUBLISHED_PORT/identity"
echo "published_rc=$?"
docker exec "$OWN_A_ID" python3 -c 'import socket,sys; print(socket.getaddrinfo(sys.argv[1], 18080))' "$OWN_B"
echo "dns_rc=$?"
docker exec "$OWN_A_ID" python3 -c 'import urllib.request,sys; print(urllib.request.urlopen("http://"+sys.argv[1]+":18080/health",timeout=2).status)' "$OWN_B"
echo "dns_http_rc=$?"
if docker exec "$OWN_A_ID" python3 -c 'import socket; print(socket.getaddrinfo("no-such-service-23.invalid", 18080))'; then echo 'missing_dns_rc=0'; else echo "missing_dns_rc=$?"; fi
```

监听反例新增自己网络中的独立实例，防止改动正常轮 B；B-local 的 `localhost` 成功与 A 到该实例 IP 的失败需要分别保存：

```sh
OWN_LOCAL_ID=$(docker run -d --name "$OWN_B_LOCAL" --network "$OWN_NET" "$OWN_TAG" python3 /app/probe_app.py --host 127.0.0.1 --state-dir /tmp/containers-state)
LOCAL_IP=$(docker inspect "$OWN_LOCAL_ID" --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
test -n "$LOCAL_IP"
docker exec "$OWN_LOCAL_ID" python3 -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:18080/health",timeout=2).status)'
if docker exec "$OWN_A_ID" python3 -c 'import sys,urllib.request; print(urllib.request.urlopen("http://"+sys.argv[1]+":18080/health",timeout=2).status)' "$LOCAL_IP"; then echo 'loopback_remote_rc=0'; else echo "loopback_remote_rc=$?"; fi
docker logs --timestamps "$OWN_LOCAL_ID"
```

需在专用 VM 额外记录 `ip -n ... route`、`bridge link`/`bridge fdb`、发布端口的 `ss`、本轮相关 conntrack 条目和自建 veth 的**有界双点 tcpdump**。若 VM 缺工具或无法把对应 netns/五元组与容器 ID 可靠对齐，相应栏目 `NOT_RUN`，不得用这篇示意值冒充原始数据。过滤拒绝仅当管理员允许在**A 自建容器的 network namespace 内**建立独立 nft table 时进行；先确认 A 宿主 PID 的 netns inode 与宿主默认 netns 不同，再以 `nsenter -t <A_PID> -n nft ...` 针对 B 的 `SERVER_IP:18080` 配置单条有界拒绝规则，按 VM 实际 nft 版本保存创建、命中、删除与重新允许请求；**不在宿主默认 namespace 加/清任何 nft/iptables 规则**。没有明确隔离/工具时直接标该反例 `NOT_RUN`，不影响 DNS/监听正反例。

完成或任意失败后仅移除本篇 A/B/B-local 与实验网络；如 nft 子实验曾创建，先在 A 的 netns 删除它的专用表，再删容器。核验不再有本篇对象及发布端口，无其它对象受影响：

```sh
docker rm -f "$OWN_A_ID" "$OWN_B_ID" "$OWN_LOCAL_ID"
echo "cleanup_containers_rc=$?"
docker network rm "$OWN_NET"
echo "cleanup_network_rc=$?"
docker ps -a --no-trunc --filter "name=containers-probe-23-"
docker network ls
```

如果网络删除因残留 endpoint 失败，只调查这一自建网络，不执行 `docker network prune`。最后检查这轮 tag 是否还被其他自建对象使用，只移除本轮 `OWN_TAG`，对比自建网络、容器、镜像和发布端口是否消失；保留原始日志副本后才清理由本轮创建的 `OWN_WORK`，不使用全局 prune。`docker image inspect` 的本地 `.Id` 不是成功推送的 manifest digest；无私有 registry 时分发摘要仍 `NOT_RUN`。当前全部 Docker/bridge/NAT/DNS/过滤实测均 `NOT_RUN`，可补跑命令和条件在此，不编造返回码或网络吞吐数据。
