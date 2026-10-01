# 02 实验入口与核对

依赖：Linux、util-linux `unshare`、允许非特权 user namespace 的实验环境。先在文章素材目录用 `sha256sum -c CHECKSUMS.sha256` 核对包，再解压到独立目录；该篇 UTS/IPC 对照仅需系统命令：

```sh
readlink /proc/self/ns/uts
unshare -Ur -u sh -c 'readlink /proc/self/ns/uts; hostname containers-own-test; hostname'
hostname
unshare -Ur -i sh -c 'readlink /proc/self/ns/ipc'
unshare -Ur -p --fork --mount-proc sh -c 'printf "pid=%s namespace=" "$$"; readlink /proc/self/ns/pid'
```

`namespace-raw.txt` 保存了实际运行的完整命令、环境由 00 的 `env-raw.txt` 锁定、原始输出和返回码。UTS/IPC 正例均返回 0；`--mount-proc` 返回 1（Operation not permitted），与预期隔离路径不同。子进程退出即恢复原宿主主机名，没有改写默认宿主配置；清理确认是末次 `hostname` 与初始值一致。namespace FD 生命周期还需专用 VM 补跑，状态 `NOT_RUN`。
