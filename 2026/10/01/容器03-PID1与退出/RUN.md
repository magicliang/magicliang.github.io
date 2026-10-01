# 03 实验入口与核对

依赖：Linux、util-linux `unshare`、允许非特权 user namespace 的环境。先在文章素材目录用 `sha256sum -c CHECKSUMS.sha256` 核对包；此命令仅向自建 namespace 中的 `sh` 发 TERM；绝不向宿主 PID 1 发送信号。

```sh
unshare -Ur -p --fork sh -c 'printf "pid=%s outer=" "$$"; grep NSpid /proc/self/status; trap '\''echo event=term_caught'\'' TERM; kill -TERM $$; printf "event=after_term pid=%s\n" "$$"'
```

预期有 handler 后收到 TERM、打印事件并正常退出；实际见 `pid1-full-raw.txt`（完整命令与退出码）和首轮 `pid1-raw.txt`，两次命令返回 0。该 procfs 沿用了外侧挂载，不能用于内侧 PID 视图验收。子进程退出即清理，宿主 PID 1 不受影响。未安装 handler 的对照、孤儿回收与重新挂载 procfs 尚未执行：本环境 `--mount-proc` 返回 Operation not permitted（02 原始日志）。在专用 VM 用自己的最小镜像重复两组程序，分别记录外侧 PID、内侧 PID、procfs mountinfo、wait 结果与清理。
