# 21 停止与故障恢复

仅专用 VM 中的**实验 daemon**，有宿主控制台和恢复权限。核对附件摘要，固定 Docker/containerd/runc 及日志驱动版本，镜像用自己的 probe-app。每次记录容器 ID、宿主 PID、signal、宽限期、业务请求起止与原始 stdout/stderr。

```sh
docker inspect containers-probe-21 --format '{{.Id}} {{.State.Pid}} {{json .HostConfig.LogConfig}}'
docker stop --time 5 containers-probe-21
docker logs --timestamps containers-probe-21
docker inspect containers-probe-21 --format '{{.State.ExitCode}} {{.State.OOMKilled}}'
```

宽限期与重启失败案例需另行创建有界可信探针，不得重启共享宿主 daemon；当前没有 daemon，运行、退出差异与清理 `NOT_RUN`。
