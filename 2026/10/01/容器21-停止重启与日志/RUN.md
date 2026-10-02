# 21 停止与故障恢复

仅专用 VM 中的**实验 daemon**，有宿主控制台和恢复权限。核对附件摘要，固定 Docker/containerd/runc 及日志驱动版本，镜像用自己的 probe-app。每次记录容器 ID、宿主 PID、signal、宽限期、业务请求起止与原始 stdout/stderr。

附件解包后可先运行 `python3 verify_probe.py --evidence-dir ./local-http-evidence`，验证普通本机进程的 HTTP 写读与 TERM 边界。以下容器命令仍须在真实 Docker 中补跑；本机 HTTP 检查不验证容器 PID 1 或 daemon。

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
