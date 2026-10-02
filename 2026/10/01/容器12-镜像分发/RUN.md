# 12 专用 registry 实验前提

需要专用 Linux VM、Docker/containerd 和仅供实验的 registry。把源码包下载到自有工作目录并校验 `CHECKSUMS.sha256`，使用 13 的 Dockerfile 为 probe-app 构建完整镜像；当前机器没有 runtime，推送、拉取与错误案例均 `NOT_RUN`。

```sh
: "${OWN_REGISTRY:?请先设置本次实验私有 registry 的 host[:port]/可选路径}"
docker version
docker image inspect containers-probe:multi --format '{{.Id}} {{json .RepoDigests}}'
docker tag containers-probe:multi "$OWN_REGISTRY/containers-probe:lab"
docker push "$OWN_REGISTRY/containers-probe:lab" > containers-12-push.log 2>&1
OWN_PUSH_STATUS=$?
cat containers-12-push.log
printf 'push exit=%s\n' "$OWN_PUSH_STATUS"
test "$OWN_PUSH_STATUS" -eq 0
```

确认本次 push 退出码为 0 后，再从 `containers-12-push.log` 的最终 `digest: sha256:...` 设置 `MANIFEST_SHA256`（仅 64 位十六进制部分），不能使用构建 image ID 或旧日志值。下面的命令必须在这一步之后执行：

```sh
: "${MANIFEST_SHA256:?请先填入本次成功 push 返回的 manifest 摘要}"
docker pull "$OWN_REGISTRY/containers-probe@sha256:$MANIFEST_SHA256"
docker image inspect "$OWN_REGISTRY/containers-probe@sha256:$MANIFEST_SHA256"
```

捕获 registry HTTP 状态、实际命令、退出码、content blob digest 与解包结果。仅对自己的 registry 运行错误凭据和缺失自建 blob 的案例；在清理 own tags、临时实例及 registry 后核对没有剩余容器。不要改动共享 registry。
