# 16 持久化实验入口

在专用 VM 固定构建器与 runtime，使用 13 的完整 probe-app 镜像。以下仅操作自建 volume 和容器；宿主 bind 测试路径也必须为自己创建的空目录。当前运行时不存在，容器的所有重建/volume 结论 `NOT_RUN`。

```sh
docker volume create containers-state-16
docker run --name containers-probe-16 -p 127.0.0.1:18080:18080 -v containers-state-16:/tmp/containers-state containers-probe:multi
curl -i -X POST --data 'only-my-lab' http://127.0.0.1:18080/state
curl -i http://127.0.0.1:18080/state
docker stop containers-probe-16
docker rm containers-probe-16
docker volume inspect containers-state-16
docker volume rm containers-state-16
```

`docker run` 与 curl 使用两个终端；清理要在检查同卷重建、bind/tmpfs、只读拒绝及备份可读之后进行。每次记录 digest、容器 ID、PID、挂载实际源和目标、HTTP 状态、文件内容、退出码、目录所有权；不能用相同路径名假定相同挂载数据。

先用更新后的源码包重新构建镜像，再在解包目录运行 `sh verify_volume.sh containers-probe:multi`。镜像在切换到 UID/GID 65532 前创建 `/tmp/containers-state`，设置所有者 65532:65532、权限 0700；上述新建空卷依赖 Docker 默认的目录复制行为，不使用 `volume-nocopy`。脚本核对非 root 写入、移除容器后同卷读回和只读挂载返回 EROFS，只清理自己的新建卷。已有卷与 bind mount 不会自动获得镜像目录权限，须先检查所有者，不能递归修改现有数据。当前仅核对 Dockerfile 的目录创建、chown/chmod 在 USER 之前；Docker 构建、新空卷复制及此 volume 检查均须在专用 VM 补跑，仍为 `NOT_RUN`。
