# 13 单阶段与多阶段

专用 Linux VM、固定 Docker/BuildKit 版本。先在素材目录用 `sha256sum -c CHECKSUMS.sha256` 校验独立源码包，再解压至全新工作目录并以其为构建上下文（只含系列源码）。读取并记录镜像真实 digest，将 `PYTHON_REF` 设为 `python:3.12-slim@sha256:<本次取得的实际摘要>`。本机没有 docker，以下全部 `NOT_RUN`。

```sh
: "${PYTHON_REF:?必须设置本次解析的基础镜像 repo@sha256:...}"
: "${HOST_PORT:?必须设置本次 VM 上自己的可用端口}"
printf '%s' "$PYTHON_REF" | grep -Eq '@sha256:[0-9a-f]{64}$' || exit 1
RUN_TAG="run-$(date -u +%Y%m%dT%H%M%SZ)-$$"
SINGLE_TAG="containers-probe:single-$RUN_TAG"
MULTI_TAG="containers-probe:multi-$RUN_TAG"
INSTANCE="containers-probe-13-$RUN_TAG"
docker version
docker build -f Dockerfile.single --build-arg PYTHON_IMAGE="$PYTHON_REF" -t "$SINGLE_TAG" . || exit 1
docker build -f Dockerfile.multi --build-arg PYTHON_IMAGE="$PYTHON_REF" -t "$MULTI_TAG" . || exit 1
docker image inspect "$SINGLE_TAG" "$MULTI_TAG"
docker run --rm --name "$INSTANCE" -p "127.0.0.1:$HOST_PORT:18080" "$MULTI_TAG"
docker image rm "$SINGLE_TAG" "$MULTI_TAG"
```

第一个终端的 `docker run` 前台阻塞时，第二个终端才执行 `curl -i "http://127.0.0.1:$HOST_PORT/ready"`（两侧须用同一端口）；停止实验后回到第一终端 Ctrl-C，确认只有自建实例退出，并检查本次镜像标签与容器均已清理。若 build 失败，保留错误与本次创建的 tag 清单，**只删除本轮确实创建的对象**，不继续跑旧标签；不得删除共享 daemon 上预先存在的 `containers-probe:multi`。预期两种镜像可启动同一服务；构建内容/大小需实测，不能预填。失败案例在自有副本中删除 COPY 输入，再 build，记录非零退出与清理；绝不改其他任务的构建目录。13 的唯一 tag 不等于 12 的本次推送摘要，12 必须另行构建并成功推送。
