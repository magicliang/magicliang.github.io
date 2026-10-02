# 35：一份负载的宿主/容器对照

状态：`NOT_RUN`。只在专用 Linux VM 测试，固定内核、架构、CPU 亲和性、父 cgroup、可用 CPU 配额、Python 版本、镜像 digest、基盘与邻居负载。共用 `bounded_load.py` 是 **一秒壁钟内的有界计算负载**，输出迭代数与实际壁钟时长；不能将 Docker 创建容器的额外时间混入进程计算时间。脚本只记录宿主/容器内可见条件与十轮原始数据，**不**得将不相同的 `cpu.max`/cpuset 组相除写成容器通用损耗。

从同篇素材目录取独立包/本篇 Dockerfile 及运行脚本，校验 SHA；`Dockerfile.c35` 仅复用 27 同样的 probe-app/bounded_load 组合，没有造一套新的负载。实际基础 Python 镜像 digest 由实验者固定，镜像需构建并推到专用仓库取实际 manifest digest；不要把本地可变 tag 当对照标识。测试命令绝不能在共享机器占用整机，CPU 和内存额度需按实验室规则设上限。

```sh
set -eu
sha256sum -c CHECKSUMS.sha256 C35_CHECKSUMS.sha256
OWN_SRC=$(mktemp -d /tmp/containers-35-src.XXXXXX)
OWN_EVIDENCE=$(mktemp -d /tmp/containers-35-evidence.XXXXXX)
tar -xzf probe-bundle.tar.gz -C "$OWN_SRC"
: "${BASE_PYTHON_IMAGE:?填入已固定 manifest digest 的 Python 基础镜像}"
: "${PROBE_IMAGE:?填入本篇两探针镜像的实际 manifest digest}"
test "$(printf '%s\n' "$BASE_PYTHON_IMAGE" "$PROBE_IMAGE" | grep -Ec '@sha256:[a-f0-9]{64}$')" -eq 2
sha256sum "$OWN_SRC/bounded_load.py" "$OWN_SRC/probe_app.py" > "$OWN_EVIDENCE/source-hashes.txt"
date -u +%FT%TZ > "$OWN_EVIDENCE/start-utc.txt"
uname -a > "$OWN_EVIDENCE/host-kernel.txt"
python3 --version > "$OWN_EVIDENCE/host-python.txt" 2>&1
docker version > "$OWN_EVIDENCE/docker-version.txt"
docker image inspect "$PROBE_IMAGE" > "$OWN_EVIDENCE/image-inspect.json"
```

`BASE_PYTHON_IMAGE` 须由操作者先用 `docker build --build-arg PYTHON_IMAGE="$BASE_PYTHON_IMAGE" -f Dockerfile.c35 "$OWN_SRC"` 的上下文实际构建、推送并核对 `PROBE_IMAGE`；上面只校验引用语法，不假装已构建。以下 host 和 container 交替十轮，后者每轮 `--rm --network none --cpus 1 --memory 128m` 限制影响；宿主进程的 cgroup 若不具备**等价** CPU/memory/cpuset 限制，则只保存环境与原始数据并标记 `NOT_COMPARABLE`。临时源目录的文件不包含客户秘密或生产凭证，容器里从同一源包构建的脚本 SHA 应与 host 一致。

```sh
for round in 1 2 3 4 5 6 7 8 9 10; do
  python3 c35_bench.py --workload "$OWN_SRC/bounded_load.py" --rounds 1 > "$OWN_EVIDENCE/host-$round.json"
  docker run --rm --network none --cpus 1 --memory 128m -i "$PROBE_IMAGE" python3 - --workload /app/bounded_load.py --rounds 1 < c35_bench.py > "$OWN_EVIDENCE/container-$round.json"
done
date -u +%FT%TZ > "$OWN_EVIDENCE/end-utc.txt"
```

每轮脚本输出程序原始 `iterations`、`seconds`、退出码和程序段迭代速率，以及观测到的 Python 版本/CPU affinity/cgroup 文件；Docker 外层启动耗时另记，不能混在迭代速率里。若任何一轮非零，`set -e` 终止并保留已有文件，报告失败数/阶段，而不是在比较时悄悄过滤。比较前还要校验两组脚本 SHA、真实 Python/依赖库版本和 CPU 配额是否一致；仅在这些条件相等的专用实验中，才按预定十轮输出局部吞吐分布，不能报告“容器平均损耗百分比”泛化到所有场景。

文件系统/网络对照须另行固定底层设备、文件来源、overlay mountinfo、首次修改 lower 到 upper 的对象状态、页缓存与是否 fsync；双 VM 网络需保存小/大包 HTTP、连接复用/超时数、双端抓包和路由/封装。`c35_bench.py` 并**没有**执行 copy-up 或跨节点访问，这两列始终 `NOT_RUN`，不能拿 CPU 正例填充；环境无双 VM 时只保留理论分析，后续由实验管理员按本篇正文和 11/25 的独立 RUN 补完专用场景。不修改共享宿主缓存、默认路由、overlay 挂载或安全策略。上述 `docker run --rm` 只生成短命自有容器，不在宿主留具名容器；记录完成后仅清理本次创建的临时源目录中的归档内容，不批量删除宿主镜像或其他任务 cgroup。

当前云端没有 Docker、可写 cgroup v2 和双 VM，所有容器/宿主性能对照、文件系统和网络结果 `NOT_RUN`；静态语法检查/页面生成不能写成性能实验。
