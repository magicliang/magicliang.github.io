# 21 停止与故障恢复

状态：**容器与 daemon 实验 `NOT_RUN`**。本云端只运行过本篇 `signal-process-raw.txt` 所记录的普通 Linux 进程信号对照。需要独占 VM 中的**实验 daemon**，有宿主控制台和恢复权限；固定 Docker/containerd/runc 与日志驱动版本。以下均只涉及自己创建的 `containers-probe-21-*`，不许在共享宿主重启默认 daemon，也不碰安全策略与默认网络。

准备：本目录含可独立取得的 `signal_probe.py`、`Dockerfile.signal`、`SIGNAL_CHECKSUMS.sha256`；共用 `probe-bundle.tar.gz` 中的 `probe_app.py` 和 `Dockerfile.multi` 用于业务请求探针。留存基础镜像实际 digest，不以浮动标签做固定版本声明。

附件解包后可先运行 `python3 verify_probe.py --evidence-dir ./local-http-evidence`，验证普通本机进程的 HTTP 写读与 TERM 边界。以下容器命令仍须在真实 Docker 中补跑；本机 HTTP 检查不验证容器 PID 1 或 daemon。

```sh
date -u +%FT%TZ
uname -a
docker version
docker context show
docker info --format '{{.LoggingDriver}} {{json .SecurityOptions}}'
sha256sum -c SIGNAL_CHECKSUMS.sha256
sha256sum -c CHECKSUMS.sha256
docker build -f Dockerfile.signal -t containers-signal:21 .
docker image inspect containers-signal:21 --format '{{.Id}} {{json .RepoDigests}}'
docker run -d --name containers-probe-21-graceful containers-signal:21 --mode graceful
docker inspect containers-probe-21-graceful --format '{{.Id}} {{.State.Pid}} {{.State.Status}} {{json .HostConfig.LogConfig}}'
docker stop --time 5 containers-probe-21-graceful
echo "graceful_stop_rc=$?"
docker logs --timestamps containers-probe-21-graceful
docker inspect containers-probe-21-graceful --format '{{.Id}} {{.State.ExitCode}} {{.State.OOMKilled}} {{.State.Error}}'

docker run -d --name containers-probe-21-delayed containers-signal:21 --mode delayed
docker inspect containers-probe-21-delayed --format '{{.Id}} {{.State.Pid}} {{.State.Status}}'
docker stop --time 1 containers-probe-21-delayed
echo "delayed_stop_rc=$?"
docker logs --timestamps containers-probe-21-delayed
docker inspect containers-probe-21-delayed --format '{{.Id}} {{.State.ExitCode}} {{.State.OOMKilled}} {{.State.Error}}'
```

每条命令分别保存开始/结束 UTC、退出码、stdout/stderr、进程 PID、daemon PID、containerd/shim 进程及事件；`docker stop` 失败后继续 inspect 和清理，不能把缺失日志补造为预期输出。比较一秒/五秒等待窗口并记录实际差别，不把普通进程 `timeout` 的 137 填入 Docker `State.ExitCode`。

daemon 重启只在专用 VM 且有恢复入口时执行；不在本文件放一条可能直接作用于共享 `docker.service` 的命令。首先在专用 VM 明确本实验 daemon 的 service 名称和 socket，由 VM 管理员重启该服务；服务操作、退出码、日志与回滚按 VM 原始记录存档。在重启**前、期间、后**固定采 20 次有界 loopback 请求，每次 `curl --max-time 2`，记录失败次数和最早恢复时刻；任何一次无法确定是否发送的请求应标未知，不记为成功。

```sh
mkdir -p lab-src
tar -xzf probe-bundle.tar.gz -C lab-src
docker build -f lab-src/Dockerfile.multi -t containers-probe:21 lab-src
docker run -d --name containers-probe-21-service -p 127.0.0.1:18084:18080 containers-probe:21
docker inspect containers-probe-21-service --format '{{.Id}} {{.State.Pid}} {{.RestartCount}} {{.State.StartedAt}}'
curl -i --max-time 2 http://127.0.0.1:18084/identity
for attempt in $(seq 1 20); do date -u +%FT%TZ; curl -i --max-time 2 http://127.0.0.1:18084/ready; echo "attempt=$attempt curl_rc=$?"; sleep 0.2; done
docker inspect containers-probe-21-service --format '{{.Id}} {{.State.Pid}} {{.RestartCount}} {{.State.StartedAt}}'
docker logs --timestamps containers-probe-21-service
```

重启应由 VM 操作者**在请求循环过程中**执行并记实际命令；如果实验服务没有独占性或不能从宿主控制台回滚，此轮直接 `NOT_RUN`，不拿业务容器的 `docker restart` 替代。清理只作用于三个自己创建的容器，核验无同名对象及对应宿主进程；若 daemon 在失败期间不可用，先从 VM 控制台恢复测试服务再清理，保留失败细节。

```sh
docker rm -f containers-probe-21-graceful containers-probe-21-delayed containers-probe-21-service
echo "cleanup_rc=$?"
docker ps -a --no-trunc --filter name=containers-probe-21-
```

此入口不声称请求循环本身已执行；实际记录必须带输入、完整命令、退出码、原始输出、预期/实测差异和清理结果。实验成功标准是可解释每轮 stop 信号与超时进程结果、daemon 换代期间每个请求与日志缺口；缺其中之一继续待验收。

## 共用 HTTP 探针的 TERM 对照

```sh
docker run -d --name containers-probe-21 -p 127.0.0.1:18080:18080 containers-probe:multi
curl -i -X POST --data 'term-lab' http://127.0.0.1:18080/state
curl -i http://127.0.0.1:18080/state
docker inspect containers-probe-21 --format '{{.Id}} {{.State.Pid}} {{json .HostConfig.LogConfig}}'
docker stop --time 5 containers-probe-21
docker logs --timestamps containers-probe-21
docker inspect containers-probe-21 --format '{{.State.ExitCode}} {{.State.OOMKilled}}'
docker rm containers-probe-21
```

探针 TERM 日志应出现 `signal: SIGTERM` 和 `stopped`，容器应在 5 秒 stop 宽限内退出 0。已接纳 HTTP 请求最多获得 3 秒网络宽限；超期连接会断开，不完整 body 不覆盖已有 state。普通本机回归另含持续滴流、悬挂及 accept 与 TERM 交错场景；真 Docker 仍需关联请求时序、容器日志和退出码补跑。重启失败案例另行创建有界可信探针，不得重启共享宿主 daemon；容器运行、停启差异与清理仍为 `NOT_RUN`。
