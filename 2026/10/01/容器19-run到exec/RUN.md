# 19 同一次启动的证据链

状态：`NOT_RUN`。当前共享云端没有 Docker/containerd/runc。只在**独占 Linux 实验 VM**运行，不修改其他容器或默认 daemon；固定 Docker/containerd/runc 版本，保留完整原始输出。压缩包包含探针、`Dockerfile.multi` 与标准库程序；以下命令以本素材目录为工作目录。第一次取用基础镜像时记录实际解析的 digest，不把 `python:3.12-slim` 可变标签当作跨时段的固定制品。

```sh
sha256sum -c CHECKSUMS.sha256
mkdir -p lab-src
tar -xzf probe-bundle.tar.gz -C lab-src
cd lab-src
date -u +%FT%TZ
uname -a
docker version
docker context show
docker info
docker build -f Dockerfile.multi -t containers-probe:19 .
docker image inspect containers-probe:19 --format '{{.Id}} {{json .RepoDigests}}'
docker run -d --name containers-probe-19-normal -p 127.0.0.1:18080:18080 containers-probe:19
docker inspect containers-probe-19-normal --format '{{.Id}} {{.State.Pid}} {{.State.Status}} {{.State.StartedAt}}'
curl -i --max-time 5 http://127.0.0.1:18080/identity
curl -i --max-time 5 http://127.0.0.1:18080/ready
docker logs --timestamps containers-probe-19-normal
docker events --since '5m' --until "$(date -u +%FT%TZ)" --filter container=containers-probe-19-normal
```

第二轮只改可控的就绪延迟。`docker run` 命令结尾明确覆盖镜像 CMD；两次请求记录实际时间与返回码，不要求精确的 10 秒整点。如果探针没有监听，先检查日志和容器状态，不用假造预期 503：

```sh
docker run -d --name containers-probe-19-delay -p 127.0.0.1:18081:18080 containers-probe:19 python3 /app/probe_app.py --host 0.0.0.0 --state-dir /tmp/containers-state --ready-delay 10
date -u +%FT%TZ
curl -i --max-time 5 http://127.0.0.1:18081/health
curl -i --max-time 5 http://127.0.0.1:18081/ready
sleep 11
date -u +%FT%TZ
curl -i --max-time 5 http://127.0.0.1:18081/ready
docker inspect containers-probe-19-delay --format '{{.Id}} {{.State.Pid}} {{.State.Status}} {{.RestartCount}}'
```

第三轮把 `create` 与 `start` 分开，并只改变入口路径；启动失败时照样查询留下的对象。每条命令分别保存开始和结束时间、退出码、stdout 与 stderr，**不要在第一条失败后停止记录**。`docker start` 的具体报错以 VM 实际版本为准，不把想得到的失败位置写成运行结果：

```sh
date -u +%FT%TZ
docker create --name containers-probe-19-bad containers-probe:19 /this-file-does-not-exist
echo "create_rc=$?"
docker start containers-probe-19-bad
echo "start_rc=$?"
docker inspect containers-probe-19-bad --format '{{.Id}} {{.State.Pid}} {{.State.Status}} {{.State.ExitCode}} {{.State.Error}}'
docker logs --timestamps containers-probe-19-bad
docker ps -a --no-trunc --filter name=containers-probe-19-
```

对启动正常的 PID，在**该 VM**读取 `/proc/<PID>/ns/{pid,mnt,net,user}`、`/proc/<PID>/cgroup`、进程启动时间及其与完整容器 ID 的映射；不要在远程客户端主机读取同名 `/proc`。记录镜像 ID/可得的 digest、容器 ID、PID、探针身份、daemon/containerd 版本及事件时间，无法取得的字段标 `NOT_RUN` 并说明原因。

清理与验证必须按本篇唯一名称逐项执行，任何失败也原样记录；仅移除这三只自建容器，不清 daemon 缓存、不改变宿主网络：

```sh
docker rm -f containers-probe-19-normal containers-probe-19-delay containers-probe-19-bad
echo "cleanup_rc=$?"
docker ps -a --no-trunc --filter name=containers-probe-19-
```
