# 18 containerd 对象关联

仅专用 VM 固定 containerd/runc 版本、snapshotter 与 namespace。先在素材目录校验包，再安装本文所用的 probe-app 完整镜像。真实环境需在运行前把 containerd tag/commit 和对应 shim 的源码位置追加到 VERSIONS，不按滚动文档猜 shim 数量。本文没有可用于所有 containerd 部署的固定 shim/PID 比例。

从仓库工作树执行 `c18_capture.sh`，先自行创建独占的 containerd namespace 与自建镜像引用、container、task（固定实际构建镜像及 digest；只使用本任务资源）。先在同名目录执行 `sha256sum -c CHECKSUMS.sha256 C18_CHECKSUMS.sha256`，并确认 `c18_capture.sh` 与 `examples/containers/c18_capture.sh` 一致。脚本本身不创建、停止或删除任何对象，不应对集群现有 namespace 使用；所有输出仅写入仓库内 `examples/containers/.lab-work/18/<stage>.XXXXXX`。目录由本系列 `.gitignore` 排除。若无法记录镜像 digest、containerd socket、snapshotter 名称或确切 shim 实现，暂停操作并保存 `NOT_RUN`，不能直接借用宿主其他 task 补图。

```sh
set -eu
: "${OWN_CONTAINERD_NS:?must be this run's exclusive namespace}"
: "${OWN_CONTAINER_ID:?must be this run's container ID}"
containerd --version
ctr namespaces list
ctr --namespace "$OWN_CONTAINERD_NS" images list
ctr --namespace "$OWN_CONTAINERD_NS" containers list
ctr --namespace "$OWN_CONTAINERD_NS" tasks list
bash source/_posts/2026-10-01-容器18-containerd对象/c18_capture.sh "$OWN_CONTAINERD_NS" "$OWN_CONTAINER_ID" before
```

`OWN_CONTAINERD_NS` 与 `OWN_CONTAINER_ID` 必须由操作者在**专用 VM** 实际创建并核对归属，不能从别人的输出复制。启动自己的 task 后再用 `running` 阶段采一轮，查看 task 主 PID 与宿主 `/proc/<pid>/stat` 第 22 字段、namespace inode 和 shim 父子关系；探针请求应关联本轮镜像和 ID。仅删除本轮自建的 image 引用，保留正在运行的 task，分别记录请求、事件与 `image-removed` 阶段结果。然后停止自有 task 并采 `stopped`，逐步删除自建 container/snapshot 与 namespace，最后核对本次 PID、挂载和目录清理。脚本的 stdout/stderr 和退出码均单独保存，`ps` 输出为空或非零并不等于内核里没有进程；事件及 HTTP 要在 VM 上另行取证。

为每个 image digest、content blob、snapshot、task ID、shim/PID 记录时间与命令，再分步停止自有 task 和删除自有 image 引用，核对对象差异与清理；当前没有 containerd，所有实际对象操作与 shim 取证仍 `NOT_RUN`。不要删除共享 namespace 内别人拥有的对象。若创建 task 失败，检查本轮 ID 的状态再选择处理，不能根据空列表清理整个 content store。
