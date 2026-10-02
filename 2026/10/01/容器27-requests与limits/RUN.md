# 27：调度、CPU 节流、内存限制与节点驱逐

状态：四类节点实验均 `NOT_RUN`。仅在独占 kind VM 使用，不在共享宿主改 cgroup 或制造内存/磁盘压力。先在本目录运行 `sha256sum -c CHECKSUMS.sha256 C27_CHECKSUMS.sha256`，解压包中的 `probe_app.py` 与 `bounded_load.py` 到一个私有构建目录，把同篇 `Dockerfile.c27` 放在该目录。它复用共同代码，`bounded_load.py` 严格限制 CPU 工作最长 2 秒、额外分配最多 32 MiB；镜像还需固定基础镜像实际摘要，按 13 的方式构建并推送到 kind 节点可达的实验 registry，保存平台 manifest digest。不把本地 image ID 当成 manifest digest，也不使用尚未拉取的模板占位符运行 Pod。

## 安全门槛与三个独立 Pod

从控制台确认集群及 kind 节点属于独占 VM，记录 `kubectl version`、节点 `containerRuntimeVersion`/`allocatable`、`mount -t cgroup2`、内核、CNI、kubelet 与 `crictl version`，确保**实际节点**使用 cgroup v2，并设置只属于本篇的命名空间。按 26 的取证方法从当前 Pod UID 和 containerID 寻找实际节点，不用 Pod 名推断节点 PID。提前留 VM 控制台、空余资源和退出/删除路径；若不存在 cgroup v2 或 registry 不可达，把相应分支标 `NOT_RUN`。`c27-resource-pods.yaml` 有三份文档：正常低配额、显式低内存、过大 CPU request；三者都只作用于新建实验命名空间。请求和实际退出结果未预设。

```sh
set -eu
OWN_NAMESPACE=c27-dedicated
: "${PROBE_IMAGE:?必须是本次构建并推送的真实 manifest digest 引用}"
printf '%s\n' "$PROBE_IMAGE" | grep -Eq '@sha256:[a-f0-9]{64}$'
! kubectl get namespace "$OWN_NAMESPACE" >/dev/null 2>&1
kubectl create namespace "$OWN_NAMESPACE"
OWN_EVIDENCE=$(mktemp -d /tmp/containers-27-evidence.XXXXXX)
kubectl get nodes -o wide > "$OWN_EVIDENCE/nodes-before.txt"
kubectl describe nodes > "$OWN_EVIDENCE/nodes-allocatable-before.txt"
sed "s|REPLACE_WITH_IMAGE_BY_DIGEST|$PROBE_IMAGE|g" c27-resource-pods.yaml > "$OWN_EVIDENCE/pods.yaml"
date -u +%FT%TZ
kubectl -n "$OWN_NAMESPACE" apply -f "$OWN_EVIDENCE/pods.yaml"
kubectl -n "$OWN_NAMESPACE" get pod -o json > "$OWN_EVIDENCE/pods-before.json"
```

若运行前同名 namespace 已存在，停止、换名并同步记录，不删现有资源。若 `apply` 失败，先检查 manifest/准入策略，不能记为“调度不足”。完成后只删本篇已创建 Pod/namespace，不通过删除所有 Pending Pod 的通配符清理。

## A：request 导致的调度等待

`c27-unschedulable` 请求 9999 核 CPU；只在节点实际可分配 CPU 远低于该值时，才预期它因资源不足保持 Pending。限定观察 60 秒，保存状态、事件、Pod UID 与所选节点（通常为空），区分资源不足和镜像/权限错误。不要在运行它的节点上寻找 `cpu.stat` 的增长，因为尚无容器进程。

```sh
kubectl -n "$OWN_NAMESPACE" describe pod c27-unschedulable > "$OWN_EVIDENCE/unschedulable-describe.txt"
kubectl -n "$OWN_NAMESPACE" get pod c27-unschedulable -o json > "$OWN_EVIDENCE/unschedulable.json"
kubectl -n "$OWN_NAMESPACE" get events --sort-by=.metadata.creationTimestamp > "$OWN_EVIDENCE/events-schedule.txt"
```

若某 VM 的 allocatable 足以调度 9999 核，这组输入不是有效的拒绝实验；记录实际值，再在本次私有目录重新生成**明显超过该节点 allocatable**的 request/limit，不能仅因为 Pod 进入 Pending 就猜测原因。

## B：CPU limit 与运行中节流

先等 `c27-baseline` Ready。命令通过 `kubectl exec` 在**同一容器 cgroup**内运行共用包的有界负载；每次负载前后分别保存 `/sys/fs/cgroup/cpu.max`、`cpu.stat`、`memory.max`、`memory.events` 原始字节及 UTC 时刻。CPU limit `100m` 在 cgroup v2 下应由节点写入对应限额，但具体值先读实际文件；比较 `nr_throttled`/`throttled_usec` 差值时还要留意同 cgroup 其它线程和采样窗口。

```sh
kubectl -n "$OWN_NAMESPACE" wait --for=condition=Ready pod/c27-baseline --timeout=120s
kubectl -n "$OWN_NAMESPACE" get pod c27-baseline -o json > "$OWN_EVIDENCE/baseline-before.json"
kubectl -n "$OWN_NAMESPACE" exec c27-baseline -c probe -- cat /sys/fs/cgroup/cpu.max /sys/fs/cgroup/cpu.stat /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.events > "$OWN_EVIDENCE/baseline-cgroup-before.txt"
kubectl -n "$OWN_NAMESPACE" exec c27-baseline -c probe -- python3 /app/bounded_load.py --seconds 2 --memory-mib 0 > "$OWN_EVIDENCE/cpu-load-raw.txt"
kubectl -n "$OWN_NAMESPACE" exec c27-baseline -c probe -- cat /sys/fs/cgroup/cpu.max /sys/fs/cgroup/cpu.stat /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.events > "$OWN_EVIDENCE/baseline-cgroup-after.txt"
kubectl -n "$OWN_NAMESPACE" get pod c27-baseline -o json > "$OWN_EVIDENCE/baseline-after.json"
```

同时按 26 的方法保存 Pod UID、容器 ID、CRI 中进程 PID、宿主 cgroup 路径与 namespace inode；否则上面只证明“容器内读到几行文件”，没有与同一 Pod 对上。如果 CLI 没有 `/sys/fs/cgroup/cpu.stat` 或文件系统为 v1，停止，记录实际挂载，不把其它机器的输出填进本篇。

## C：内存限制与容器 OOM

`c27-memory` 是一次性的 32 MiB limit 测试，只运行 `bounded_load.py --memory-mib 32`，没有后台守护进程或无限分配。解释器/运行库也消耗内存；它可能在分配时触发组内 OOM，也可能在某个环境下未触发或在开始前被别的故障阻断。等待 30 秒后保存 Pod JSON、事件、可取得的先前日志和容器状态；若 cgroup 消失导致无法读取 `memory.events`，标注证据缺失并在专用节点同步采样重试，**不能仅凭退出码 137 归因为 memory.max OOM**。

```sh
kubectl -n "$OWN_NAMESPACE" get pod c27-memory -o json > "$OWN_EVIDENCE/memory-before.json"
sleep 5
kubectl -n "$OWN_NAMESPACE" get pod c27-memory -o json > "$OWN_EVIDENCE/memory-after.json"
kubectl -n "$OWN_NAMESPACE" describe pod c27-memory > "$OWN_EVIDENCE/memory-describe.txt"
kubectl -n "$OWN_NAMESPACE" logs c27-memory -c load --timestamps > "$OWN_EVIDENCE/memory-logs.txt"
```

两次 JSON 必须在**不同时间点**实际执行，按真实开始/结束 UTC 时间记录，建议间隔不超过 30 秒；若日志命令因容器从未创建而失败，也保存退出码。OOM 验收同时对照 `memory.events` 的 `oom`/`oom_kill` 增量、容器 `terminated.reason` 与对应节点事件；若没有采到内核计数或对应 ID，则报告“容器状态提示 OOM，内核侧待补证”，不算完整 `LAB_VERIFIED`。

## D：节点压力驱逐只做专用 VM 的二次实验

不要通过在此云端或共享节点启动通用 `stress --vm`、写满根目录、改 kubelet 驱逐阈值来补齐第四栏。需要由专用 VM 管理者预先给出节点/数据盘预算、驱逐信号阈值、恢复控制台及硬停止条件，在**自建测试节点**上单独进行有上限的压力注入；记录 Node `MemoryPressure`/`DiskPressure`、kubelet eviction 日志、受害 Pod UID/事件、pressure 来源与恢复请求结果。驱逐可能影响多个 Pod，删除一个测试 Pod 不等于节点已恢复；与 limit OOM 必须使用**不同的原始证据**。本篇没有可保证安全的通用注压脚本与真实 VM，D 维持 `NOT_RUN`，不是用 C 的结果替代。

在获批且有专用负载/恢复方案后，用以下只读入口在实际目标节点采样；`OWN_NODE` 必须取自本篇已调度 Pod 的 `spec.nodeName`，而不是控制终端上的任意节点。操作员另行记录每一次专用压力工具的确切命令、上限、超时与恢复动作；在没有这份实验室特定方案前不得执行注压。

```sh
OWN_NODE=$(kubectl -n "$OWN_NAMESPACE" get pod c27-baseline -o jsonpath='{.spec.nodeName}')
test -n "$OWN_NODE"
kubectl get node "$OWN_NODE" -o json > "$OWN_EVIDENCE/node-pressure-before.json"
kubectl -n "$OWN_NAMESPACE" get pod -o json > "$OWN_EVIDENCE/pods-pressure-before.json"
```

只在专用 VM 管理者批准并执行有明确停止条件的独立注压/恢复方案之后，再运行下一组命令；两组之间不能原样紧贴运行当作驱逐证据。

```sh
kubectl get node "$OWN_NODE" -o json > "$OWN_EVIDENCE/node-pressure-after.json"
kubectl -n "$OWN_NAMESPACE" get pod -o json > "$OWN_EVIDENCE/pods-pressure-after.json"
```

## 清理与报告

清理前保留全量 `kubectl get pods -o json`、事件、节点资源数值、探针输出、命令返回码与所选 cgroup 快照；将 A/B/C/D 四栏分开报告。只在证实此命名空间由本轮创建后执行下列命令，再检查残留并由 VM 管理者核对节点正常：

```sh
kubectl -n "$OWN_NAMESPACE" delete pod c27-baseline c27-memory c27-unschedulable --ignore-not-found --wait=true --timeout=120s
kubectl delete namespace "$OWN_NAMESPACE" --wait=true --timeout=120s
kubectl get nodes -o wide
```

`--ignore-not-found` 仅对本轮列出的三个名字有效，不能放宽删除范围；删除失败保留输出，不操作其他任务的 Pod 或节点。当前云端无 kind、cgroup v2 可写挂载或专用 VM，A–D 全部 `NOT_RUN`。
