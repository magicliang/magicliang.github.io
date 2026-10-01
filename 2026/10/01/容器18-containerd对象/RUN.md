# 18 containerd 对象关联

仅专用 VM 固定 containerd/runc 版本、snapshotter 与 namespace。先在素材目录校验包，再安装本文所用的 probe-app 完整镜像。真实环境需在运行前把 containerd tag/commit 和对应 shim 的源码位置追加到 VERSIONS，不按滚动文档猜 shim 数量。

```sh
containerd --version
ctr namespaces list
ctr --namespace "$OWN_CONTAINERD_NS" images list
ctr --namespace "$OWN_CONTAINERD_NS" containers list
ctr --namespace "$OWN_CONTAINERD_NS" tasks list
```

为每个 image digest、content blob、snapshot、task ID、shim/PID 记录时间与命令，再分步停止自有 task 和删除自有 image 引用，核对对象差异与清理；当前没有 containerd，`NOT_RUN`。不要删除共享 namespace 内别人拥有的对象。
