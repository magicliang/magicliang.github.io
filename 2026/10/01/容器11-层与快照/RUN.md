# 11 OverlayFS 实验前提

仅在专用 Linux VM、允许创建私有 mount namespace 且存储支持 OverlayFS 时运行。将最小源码包（含 10 的 `oci_layout.py`）下载到独立目录，先校验 `CHECKSUMS.sha256`；脚本仅生成 OCI 布局，不会执行 mount。

```sh
unshare --user --map-root-user --mount sh
mkdir -p /tmp/containers-11-own/{lower,upper,work,merged}
printf 'old\n' > /tmp/containers-11-own/lower/config
mount --make-rprivate /
mount -t overlay overlay -o lowerdir=/tmp/containers-11-own/lower,upperdir=/tmp/containers-11-own/upper,workdir=/tmp/containers-11-own/work /tmp/containers-11-own/merged
cat /tmp/containers-11-own/merged/config
```

`mount --make-rprivate /` **只能在已核实为私有的专用 mount namespace 内执行**，禁止在共享宿主运行。接下来仅在自有 merged 路径写/删，检查 lower/upper、mountinfo，先 `umount` 再退出并由宿主核对目录无挂载，删除自建目录。当前云端挂载不可用，正反案例及清理 `NOT_RUN`；以上是补跑方案不是原始结果。
