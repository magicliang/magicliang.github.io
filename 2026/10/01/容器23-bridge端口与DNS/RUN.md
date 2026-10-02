# 23 端口与解析的三条路径

状态：`NOT_RUN`；共享云端缺 Docker/`ip`/专用 VM。**仅独占 Linux 实验 VM** 使用自建 `containers-net-23` bridge 和三个自建容器，固定 Docker/libnetwork、iproute2、kernel、日志驱动与本次镜像实际 ID。先校验同名附件并解压；下方所有新对象使用唯一名称，冲突则中止，不改共享网络、全局 DNS 或宿主默认防火墙。命令逐条保存开始结束 UTC、原始 stdout/stderr 与退出码，不把配置表充作抓包。

```sh
date -u +%FT%TZ
uname -a
docker version
docker info --format '{{.Driver}} {{json .SecurityOptions}}'
ip -V
sha256sum -c CHECKSUMS.sha256
mkdir -p lab-src
tar -xzf probe-bundle.tar.gz -C lab-src
docker build -f lab-src/Dockerfile.multi -t containers-probe:23 lab-src
docker image inspect containers-probe:23 --format '{{.Id}} {{json .RepoDigests}}'
docker network ls
docker network create --driver bridge containers-net-23
docker run -d --name containers-probe-23-b --network containers-net-23 -p 127.0.0.1:18085:18080 containers-probe:23
docker run -d --name containers-probe-23-a --network containers-net-23 containers-probe:23
docker network inspect containers-net-23
docker inspect containers-probe-23-b --format '{{.Id}} {{.State.Pid}} {{json .NetworkSettings.Networks}} {{json .HostConfig.PortBindings}}'
docker inspect containers-probe-23-a --format '{{.Id}} {{.State.Pid}} {{json .NetworkSettings.Networks}}'
SERVER_IP=$(docker inspect containers-probe-23-b --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
test -n "$SERVER_IP"
docker exec containers-probe-23-a python3 -c 'import sys,urllib.request; print(urllib.request.urlopen("http://"+sys.argv[1]+":18080/identity",timeout=2).read().decode())' "$SERVER_IP"
echo "direct_rc=$?"
curl -i --max-time 2 http://127.0.0.1:18085/identity
echo "published_rc=$?"
docker exec containers-probe-23-a python3 -c 'import socket; print(socket.getaddrinfo("containers-probe-23-b", 18080))'
echo "dns_rc=$?"
docker exec containers-probe-23-a python3 -c 'import urllib.request; print(urllib.request.urlopen("http://containers-probe-23-b:18080/health",timeout=2).status)'
echo "dns_http_rc=$?"
docker exec containers-probe-23-a python3 -c 'import socket; print(socket.getaddrinfo("no-such-service-23.invalid", 18080))'
echo "missing_dns_rc=$?"
```

监听反例新增自己网络中的独立实例，防止改动正常轮 B；B-local 的 `localhost` 成功与 A 到该实例 IP 的失败需要分别保存：

```sh
docker run -d --name containers-probe-23-b-local --network containers-net-23 containers-probe:23 python3 /app/probe_app.py --host 127.0.0.1 --state-dir /tmp/containers-state
LOCAL_IP=$(docker inspect containers-probe-23-b-local --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
test -n "$LOCAL_IP"
docker exec containers-probe-23-b-local python3 -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:18080/health",timeout=2).status)'
docker exec containers-probe-23-a python3 -c 'import sys,urllib.request; print(urllib.request.urlopen("http://"+sys.argv[1]+":18080/health",timeout=2).status)' "$LOCAL_IP"
echo "loopback_remote_rc=$?"
docker logs --timestamps containers-probe-23-b-local
```

需在专用 VM 额外记录 `ip -n ... route`、`bridge link`/`bridge fdb`、发布端口的 `ss`、本轮相关 conntrack 条目和自建 veth 的**有界双点 tcpdump**。若 VM 缺工具或无法把对应 netns/五元组与容器 ID 可靠对齐，相应栏目 `NOT_RUN`，不得用这篇示意值冒充原始数据。过滤拒绝仅当管理员允许在**A 自建容器的 network namespace 内**建立独立 nft table 时进行；先确认 A 宿主 PID 的 netns inode 与宿主默认 netns 不同，再以 `nsenter -t <A_PID> -n nft ...` 针对 B 的 `SERVER_IP:18080` 配置单条有界拒绝规则，按 VM 实际 nft 版本保存创建、命中、删除与重新允许请求；**不在宿主默认 namespace 加/清任何 nft/iptables 规则**。没有明确隔离/工具时直接标该反例 `NOT_RUN`，不影响 DNS/监听正反例。

完成或任意失败后仅移除本篇 A/B/B-local 与实验网络；如 nft 子实验曾创建，先在 A 的 netns 删除它的专用表，再删容器。核验不再有本篇对象及发布端口，无其它对象受影响：

```sh
docker rm -f containers-probe-23-a containers-probe-23-b containers-probe-23-b-local
echo "cleanup_containers_rc=$?"
docker network rm containers-net-23
echo "cleanup_network_rc=$?"
docker ps -a --no-trunc --filter name=containers-probe-23-
docker network ls
```

如果网络删除因残留 endpoint 失败，只调查这一自建网络，不执行 `docker network prune`。当前全部 Docker/bridge/NAT/DNS/过滤实测均 `NOT_RUN`，可补跑命令和条件在此，不编造返回码或网络吞吐数据。
