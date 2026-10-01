# 08 VM 补跑入口

当前除 00 的 `/proc/self/status` 权限基线与 02 的 `--mount-proc` 拒绝外，还执行了独立 seccomp 可信程序：`seccomp-raw.txt` 是安装仅作用于该实验进程的过滤器后 `getpid` 被拒、`getppid` 允许的原始输出；没有运行容器、capability drop 或 LSM 对照，整篇计划实验依旧 `NOT_RUN`。不能关闭宿主 LSM 或默认安全机制。

在本目录执行 `sha256sum -c SECCOMP_CHECKSUMS.sha256`，本目录的 `seccomp_probe.c` 与 `examples/containers/seccomp_probe.c` 相同，只支持 x86_64 Linux：

```sh
cc -std=c11 -Wall -Wextra -Werror seccomp_probe.c -o /tmp/containers-seccomp-probe
/tmp/containers-seccomp-probe
python3 -c 'from pathlib import Path; Path("/tmp/containers-seccomp-probe").unlink()'
```

程序只允许在可信自编进程内安装 filter；退出即销毁该过滤器。发生安装失败时保留 errno，不能为了通过而放宽全局策略。临时文件只删除自己创建的二进制。

```sh
grep -E '^(CapEff|CapBnd|Seccomp|NoNewPrivs):' /proc/self/status
unshare -Ur sh -c 'grep -E "^(CapEff|Seccomp|NoNewPrivs):" /proc/self/status'
```

后续专用 VM 对照还需真实 drop capability、读取具体 LSM profile/审计事件并观察同一可信操作的允许和拒绝条件；失败时移除整个仅供实验的进程环境，不放宽宿主策略。共同归档里没有新增过滤器，专项源码独立链接与独立校验，不能将本次局部成功标为完整隔离边界验收。
