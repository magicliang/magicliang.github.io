# 17 OCI bundle 与状态

需要专用 Linux VM、固定 runc 版本和具有完整 rootfs 的自建 probe-app 镜像。先校验本目录 `CHECKSUMS.sha256`，解压源码包并用 13 的 Dockerfile 创建可信镜像；生成 bundle 时锁定解包 rootfs 的来源/digest 与配置，不能把 10 的“只有脚本”的 layout 当可运行 rootfs。

```sh
runc --version
runc spec --bundle "$OWN_BUNDLE"
runc --root "$OWN_RUNC_ROOT" create --bundle "$OWN_BUNDLE" containers-17-own
runc --root "$OWN_RUNC_ROOT" state containers-17-own
runc --root "$OWN_RUNC_ROOT" start containers-17-own
runc --root "$OWN_RUNC_ROOT" state containers-17-own
runc --root "$OWN_RUNC_ROOT" delete containers-17-own
```

先由实验者创建 `OWN_BUNDLE` 和 `OWN_RUNC_ROOT` 并确保仅属于本实验，保存 config.json、rootfs digest、ID、宿主 PID、namespace/cgroup、各步输出、退出码、原始 HTTP 响应。错误 config 只在副本中改，失败后核对相关进程、挂载与目录无残留；共享云端 runc 未安装，正负例 `NOT_RUN`。
