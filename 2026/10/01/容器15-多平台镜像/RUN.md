# 15 多平台验收入口

仅专用 VM 的固定 BuildKit/buildx 版本与两种确实可运行的平台；记录 x86_64 与 arm64 的节点内核、CPU 架构、原生/仿真标签和基础镜像实际 digest。当前只有 x86_64 Linux、没有运行时，两平台构建和执行 `NOT_RUN`。

```sh
docker buildx version
docker buildx build -f Dockerfile.single --platform linux/amd64,linux/arm64 --build-arg PYTHON_IMAGE="$PINNED_MULTIARCH_BASE" --push -t "$OWN_REGISTRY/containers-probe:15" .
docker buildx imagetools inspect "$OWN_REGISTRY/containers-probe:15"
```

`PINNED_MULTIARCH_BASE` 必须是实际拥有两平台描述符的固定 index digest；`OWN_REGISTRY` 必须是自建受控 registry。两台节点分别拉取按平台选择的制品并请求 `/identity`；分别保存 index digest、每平台 manifest digest、容器 ID、内核、CPU 与清理输出。不要把仿真结果混进原生性能结论。
