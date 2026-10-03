# 16 持久化实验入口

在专用 VM 固定构建器与 runtime，使用 13 的完整 probe-app 镜像。以下仅操作自建 volume 和容器；宿主 bind 测试路径也必须为自己创建的空目录。当前运行时不存在，容器的所有重建/volume 结论 `NOT_RUN`。

```sh
set -eu
: "${PROBE_IMAGE:?须先在本次 VM 构建完整镜像并记录 image ID}"
: "${HOST_PORT:?须选择本次 VM 的可用 loopback 端口}"
RUN_TAG="lab-16-$(date -u +%Y%m%dT%H%M%SZ)-$$"
VOLUME="containers-state-$RUN_TAG"
FIRST="containers-probe-$RUN_TAG-first"
SECOND="containers-probe-$RUN_TAG-second"
docker image inspect "$PROBE_IMAGE" --format '{{.Id}}'
docker volume create "$VOLUME"
docker run -d --name "$FIRST" -p "127.0.0.1:$HOST_PORT:18080" -v "$VOLUME:/tmp/containers-state" "$PROBE_IMAGE"
curl --retry 5 --retry-delay 1 --retry-connrefused -i "http://127.0.0.1:$HOST_PORT/health"
curl -i -X POST --data 'only-my-lab' "http://127.0.0.1:$HOST_PORT/state"
curl -i "http://127.0.0.1:$HOST_PORT/state"
docker stop "$FIRST"
docker rm "$FIRST"
docker volume inspect "$VOLUME"
docker run -d --name "$SECOND" -p "127.0.0.1:$HOST_PORT:18080" -v "$VOLUME:/tmp/containers-state" "$PROBE_IMAGE"
curl --retry 5 --retry-delay 1 --retry-connrefused -i "http://127.0.0.1:$HOST_PORT/state"
docker stop "$SECOND"
docker rm "$SECOND"
docker volume rm "$VOLUME"
```

上面的 `docker run -d` 与 curl 可以在同一终端完成；执行前记录本轮唯一的 `RUN_TAG`、`VOLUME`、`FIRST`、`SECOND` 与真实镜像 ID，每次记录 digest、容器 ID、PID、挂载实际源和目标、HTTP 状态、文件内容、退出码、目录所有权。若中途失败，先记录已创建哪些自有容器/卷，随后只清理这些对象，不按固定名称删除旧卷。本块只验新空卷同卷重建；bind/tmpfs、已有卷所有权、只读拒绝及备份可读还要分别运行，不能因为本块成功就提前标为完整实验。

先用更新后的源码包重新构建镜像，再在解包目录运行 `sh verify_volume.sh "$PROBE_IMAGE"`。镜像在切换到 UID/GID 65532 前创建 `/tmp/containers-state`，设置所有者 65532:65532、权限 0700；上述新建空卷依赖 Docker 默认的目录复制行为，不使用 `volume-nocopy`。脚本核对非 root 写入、移除容器后同卷读回和只读挂载返回 EROFS，只清理自己的新建卷。已有卷与 bind mount 不会自动获得镜像目录权限，须先检查所有者，不能递归修改现有数据。当前仅核对 Dockerfile 的目录创建、chown/chmod 在 USER 之前；Docker 构建、新空卷复制及此 volume 检查均须在专用 VM 补跑，仍为 `NOT_RUN`。
