# 09 教学启动器入口

核对源码包的 `CHECKSUMS.sha256` 并解压。只在自己新建的空目录编译，固定只执行自编 `process_probe`：

```sh
owned=$(mktemp -d /tmp/containers-launcher-XXXXXX)
gcc -std=c11 -Wall -Wextra -Werror -O2 process_probe.c -o "$owned/process_probe"
gcc -std=c11 -Wall -Wextra -Werror -O2 teaching_launcher.c -o "$owned/teaching_launcher"
(cd "$owned" && ./teaching_launcher)
rm -r "$owned"
```

`launcher-raw.txt` 有本次真实路径、编译/运行每步退出码、进程事件、删除结果；`launcher-failure-raw.txt` 有刻意缺少同目录 `process_probe` 的失败路径（退出 1）、父进程回收与目录清理。两条有限路径 `LAB_VERIFIED`，完整 09 验收仍 `NOT_RUN`：未实现 mount、PID、net、cgroup、安全约束或映射失败清理，禁止传入不可信程序。
