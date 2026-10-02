# 20 rootless 不是 USER

状态：`NOT_RUN`；本云端没有 Docker 或可委派的 cgroup v2。只在独占 Linux VM、两个相互独立且版本固定的实验 daemon 上执行；rootful 由 VM 管理员准备，rootless 使用专门的非特权帐号。**不要在共享宿主上安装/启动 daemon、修改默认 context、网络或 cgroup 委派。** 以下将 `ROOTFUL_CONTEXT` 和 `ROOTLESS_CONTEXT` 设为两个事先核实的 *不同* Docker context 名称；先确认 `docker --context … info` 指向不同 socket/daemon。镜像标签可能漂移，只有两个 daemon 的本地镜像 `Id` 相同才能宣称比较同一字节制品。

预备（在本篇素材目录）：

```sh
sha256sum -c CHECKSUMS.sha256
mkdir -p lab-src
tar -xzf probe-bundle.tar.gz -C lab-src
date -u +%FT%TZ
uname -a
docker context ls
: "${ROOTFUL_CONTEXT:?specify isolated rootful daemon context}"
: "${ROOTLESS_CONTEXT:?specify isolated rootless daemon context}"
docker --context "$ROOTFUL_CONTEXT" version
docker --context "$ROOTLESS_CONTEXT" version
docker --context "$ROOTFUL_CONTEXT" info --format '{{json .SecurityOptions}} {{.CgroupDriver}} {{.Driver}}'
docker --context "$ROOTLESS_CONTEXT" info --format '{{json .SecurityOptions}} {{.CgroupDriver}} {{.Driver}}'
docker --context "$ROOTFUL_CONTEXT" build -f lab-src/Dockerfile.multi -t containers-probe:20 lab-src
docker --context "$ROOTLESS_CONTEXT" build -f lab-src/Dockerfile.multi -t containers-probe:20 lab-src
docker --context "$ROOTFUL_CONTEXT" image inspect containers-probe:20 --format '{{.Id}} {{json .RepoDigests}}'
docker --context "$ROOTLESS_CONTEXT" image inspect containers-probe:20 --format '{{.Id}} {{json .RepoDigests}}'
```

对两个 daemon 的镜像都显式保持 `USER 65532:65532`，只在 VM 上发布 loopback 高端口：

```sh
docker --context "$ROOTFUL_CONTEXT" run -d --name containers-probe-20-rootful -p 127.0.0.1:18082:18080 containers-probe:20
docker --context "$ROOTLESS_CONTEXT" run -d --name containers-probe-20-rootless -p 127.0.0.1:18083:18080 containers-probe:20
docker --context "$ROOTFUL_CONTEXT" inspect containers-probe-20-rootful --format '{{.Id}} {{.State.Pid}} {{.Config.User}}'
docker --context "$ROOTLESS_CONTEXT" inspect containers-probe-20-rootless --format '{{.Id}} {{.State.Pid}} {{.Config.User}}'
curl -i --max-time 5 http://127.0.0.1:18082/identity
curl -i --max-time 5 http://127.0.0.1:18083/identity
docker --context "$ROOTFUL_CONTEXT" exec containers-probe-20-rootful id
docker --context "$ROOTLESS_CONTEXT" exec containers-probe-20-rootless id
```

`curl` 应在**对应 daemon 所在的 VM**执行；远端 context 时客户端的 `127.0.0.1` 不是 daemon 主机。获取各 daemon 的真实宿主 PID 与上面 inspect 的两只应用宿主 PID 后，在 VM 上分别读取 `/proc/<pid>/status` 的 `Uid`、`CapEff`、`/proc/<pid>/uid_map`、`gid_map`、`cgroup`，并保存 `stat -fc %T /sys/fs/cgroup`、可用控制器、父级委派路径及权限。PID 变量必须使用当次输出，不能直接从文章填数字。

资源边界：只在专用 VM 的 rootless context 创建自己命名的 CPU 配额实验容器；如果委派不存在，记录 CLI 返回码和原始错误后停止，不按 cgroup v2 路径强行读取。负载限 2 秒且仅在自己的容器内执行，逐次读取其目标 cgroup 的 `cpu.max`/`cpu.stat`，先保留原始值，再运行并记录增量：

```sh
docker --context "$ROOTLESS_CONTEXT" run -d --name containers-probe-20-cpu --cpus=0.5 containers-probe:20
echo "cpu_create_rc=$?"
docker --context "$ROOTLESS_CONTEXT" inspect containers-probe-20-cpu --format '{{.Id}} {{.State.Pid}} {{.State.Status}} {{.State.Error}}'
docker --context "$ROOTLESS_CONTEXT" cp lab-src/bounded_load.py containers-probe-20-cpu:/tmp/bounded_load.py
docker --context "$ROOTLESS_CONTEXT" exec containers-probe-20-cpu python3 /tmp/bounded_load.py --seconds 2
echo "bounded_load_rc=$?"
```

失败时可能 `cp`/`exec` 也不能运行；每条命令分别记开始/结束时间、退出码、stdout/stderr，不把脚本中的 `echo` 当成功证据。严禁在共享主机执行、修改 `ip_unprivileged_port_start` 或宽松 socket 权限。完成后只移除本篇三只自建容器，验证两个 context 均无对应名称，按管理者要求恢复实验用户服务：

```sh
docker --context "$ROOTFUL_CONTEXT" rm -f containers-probe-20-rootful
docker --context "$ROOTLESS_CONTEXT" rm -f containers-probe-20-rootless containers-probe-20-cpu
docker --context "$ROOTFUL_CONTEXT" ps -a --no-trunc --filter name=containers-probe-20-
docker --context "$ROOTLESS_CONTEXT" ps -a --no-trunc --filter name=containers-probe-20-
```

当前仅 05 的 `unshare -Ur` 对 Linux userns 本身有局部证据；上述 Docker daemon 身份、端口、挂载和 cgroup 对照全部仍为 `NOT_RUN`。最少交付：环境版本、完整输入/命令、每条命令退出码和原始输出、预期与实际差异、daemon/socket/容器完整 ID/PID/映射、清理结果；不能填造现场数字。
