# 13 单阶段与多阶段

专用 Linux VM、固定 Docker/BuildKit 版本。先在素材目录用 `sha256sum -c CHECKSUMS.sha256` 校验独立源码包，再解压至全新工作目录并以其为构建上下文（只含系列源码）。读取并记录镜像真实 digest，将 `PYTHON_REF` 设为 `python:3.12-slim@sha256:<本次取得的实际摘要>`。本机没有 docker，以下全部 `NOT_RUN`。

```sh
docker version
docker build -f Dockerfile.single --build-arg PYTHON_IMAGE="$PYTHON_REF" -t containers-probe:single .
docker build -f Dockerfile.multi --build-arg PYTHON_IMAGE="$PYTHON_REF" -t containers-probe:multi .
docker image inspect containers-probe:single containers-probe:multi
docker run --rm --name containers-probe-13 -p 127.0.0.1:18080:18080 containers-probe:multi
curl -i http://127.0.0.1:18080/ready
docker image rm containers-probe:single containers-probe:multi
```

run 与 curl 需要两个终端。预期两种镜像可启动同一服务；构建内容/大小需要实测，不能预填。失败案例在自有副本中删除 COPY 输入，再 build，记录非零退出与清理；绝不改其他任务的构建目录。
