# 01 实验入口与核对

依赖：Linux、gcc、POSIX shell、可读 `/proc`。在文章素材目录先执行 `sha256sum -c CHECKSUMS.sha256`，解压包到独立目录，在包的根目录执行：

```sh
gcc -std=c11 -Wall -Wextra -Werror -O2 process_probe.c -o /tmp/containers-process-probe
/tmp/containers-process-probe inherit
/tmp/containers-process-probe cloexec
/tmp/containers-process-probe zombie
/tmp/containers-process-probe invalid
rm -f /tmp/containers-process-probe
```

`process-raw.txt` 含执行时间、完整参数、stdout/stderr、所有程序退出码；本次 gcc 返回 0。预期默认 FD 跨 `exec` 保留，CLOEXEC 关闭；短时 zombie 在 `waitpid` 后回收；无效参数返回 2。实际三种正常模式均返回 0，无效参数 2，与预期一致。运行器只删除自己编译的 `/tmp/containers-process-probe`；自建临时文件由程序打开并立即删除路径，后续关闭 FD。信号终止和宿主容器双侧对照仍 `NOT_RUN`。
