# 12 专用 registry 实验前提

需要专用 Linux VM、Docker/containerd 和仅供实验的 registry。把源码包下载到自有工作目录并校验 `CHECKSUMS.sha256`，在解压目录用共用 `Dockerfile.multi` **本次重新构建** probe-app 镜像；只使用实际查询得到的基础镜像 digest，不用默认浮动 tag。当前机器没有 runtime，推送、拉取与错误案例均 `NOT_RUN`。以下整个块应在**同一 shell** 运行，日志写入新建自有目录，避免覆盖历史日志：

```sh
: "${OWN_REGISTRY:?请先设置本次实验私有 registry 的 host[:port]/可选路径}"
: "${PYTHON_IMAGE_REF:?设置本次确认的平台基础镜像 repo@sha256:...}"
printf '%s' "$PYTHON_IMAGE_REF" | grep -Eq '@sha256:[0-9a-f]{64}$' || { echo 'base image must use repo@sha256:<64 hex>' >&2; exit 1; }
RUN_DIR=$(mktemp -d ./experiment-12.XXXXXX)
RUN_TAG="run-$(date -u +%Y%m%dT%H%M%SZ)-$$"
BUILD_TAG="containers-probe:$RUN_TAG"
docker version
docker build --build-arg "PYTHON_IMAGE=$PYTHON_IMAGE_REF" -f Dockerfile.multi -t "$BUILD_TAG" . > "$RUN_DIR/build.log" 2>&1
OWN_BUILD_STATUS=$?
printf 'build exit=%s tag=%s base=%s evidence=%s\n' "$OWN_BUILD_STATUS" "$BUILD_TAG" "$PYTHON_IMAGE_REF" "$RUN_DIR"
test "$OWN_BUILD_STATUS" -eq 0 || exit 1
docker image inspect "$BUILD_TAG" --format '{{.Id}} {{json .RepoDigests}}' > "$RUN_DIR/local-image.txt"
docker tag "$BUILD_TAG" "$OWN_REGISTRY/containers-probe:$RUN_TAG"
test "$?" -eq 0 || exit 1
docker push "$OWN_REGISTRY/containers-probe:$RUN_TAG" > "$RUN_DIR/push.log" 2>&1
OWN_PUSH_STATUS=$?
cat "$RUN_DIR/push.log"
printf 'push exit=%s\n' "$OWN_PUSH_STATUS"
test "$OWN_PUSH_STATUS" -eq 0
```

确认本次 push 退出码为 0 后，再从 **本次 `$RUN_DIR/push.log`** 的最终 `digest: sha256:...` 设置 `PUSH_SHA256`（仅 64 位十六进制部分），不能使用本地 image ID、先前的 `RepoDigests` 或旧日志值。先记录并验证此引用实际返回单平台 manifest 还是 index：`docker manifest inspect "$OWN_REGISTRY/containers-probe@sha256:$PUSH_SHA256"`；若是单平台 manifest，`MANIFEST_SHA256=$PUSH_SHA256`。如果有 `manifests` 数组，应按当前平台选中**本次 index 中实际存在**的子 manifest digest，设置 `MANIFEST_SHA256` 为该摘要，分别记录 index 与 manifest，**不能把 index digest 标成该子 manifest digest**。记录查询命令、响应类型、镜像 ID 和本次推送日志，不能脱离 `$RUN_DIR` 混用历史数据。下面的拉取命令必须在本次 push/引用核验后执行：

```sh
: "${MANIFEST_SHA256:?请先填入本次成功 push 返回的 manifest 摘要}"
docker pull "$OWN_REGISTRY/containers-probe@sha256:$MANIFEST_SHA256"
docker image inspect "$OWN_REGISTRY/containers-probe@sha256:$MANIFEST_SHA256"
```

捕获 registry HTTP 状态、实际命令、退出码、content blob digest 与解包结果。仅对自己的 registry 运行错误凭据和缺失自建 blob 的案例；只有在保存本次原始日志及 digest 后才清理**本次生成**的唯一 tag、镜像与私有 registry 资源，并确认没有剩余容器；不要批量删除现有镜像或共享 registry。失败的 build/push 不得跳过保留日志和自己生成资源的确认，不能用预期值补做 pull。
