# 12 专用 registry 实验前提

需要专用 Linux VM、Docker/containerd 和仅供实验的 registry。把源码包下载到自有工作目录并校验 `CHECKSUMS.sha256`，使用 13 的 Dockerfile 为 probe-app 构建完整镜像；当前机器没有 runtime，推送、拉取与错误案例均 `NOT_RUN`。

```sh
docker version
docker image inspect containers-probe:lab --format '{{.Id}} {{json .RepoDigests}}'
docker push "$OWN_REGISTRY/containers-probe:lab"
docker pull "$OWN_REGISTRY/containers-probe@sha256:$MANIFEST_SHA256"
docker image inspect "$OWN_REGISTRY/containers-probe@sha256:$MANIFEST_SHA256"
```

运行前必须设 `OWN_REGISTRY` 为实验私有 registry、`MANIFEST_SHA256` 为本次真实 push 返回的 manifest 摘要，不能粘贴旧日志中的值。捕获 registry HTTP 状态、实际命令、退出码、content blob digest 与解包结果。仅对自己的 registry 运行错误凭据和缺失自建 blob 的案例；在清理 own tags、临时实例及 registry 后核对没有剩余容器。不要改动共享 registry。
