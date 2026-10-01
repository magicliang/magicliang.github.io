# 04 实验入口

核对 `CHECKSUMS.sha256` 后解压源码包，在 Linux 中执行（只影响新 user namespace 内进程）：

```sh
owned=$(mktemp -d /tmp/containers-root-XXXXXX)
unshare -Ur python3 root_probe.py "$owned"
rmdir "$owned"
```

`root-raw.txt` 保存实际目录名、完整入口及各步退出码。本次 `os.chroot` 和保留 FD 的读取返回 0，自建目录清理返回 0；这是对“chroot 自动撤销旧 FD”假设的反例。没有 mount 操作，根挂载、`pivot_root`、mountinfo 清理均 `NOT_RUN`。补跑仅在专用 VM：进入自己的 mount namespace，把自己的挂载树设为 private，以自建 rootfs 做 `pivot_root` 后检查旧根与 mountinfo；先停止实验进程，再卸载自建挂载，核对宿主目录无残留。不对共享宿主根挂载做任何传播改写。
