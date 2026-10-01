# 20 rootless 不是 USER

需专用 VM 中两个相互独立且版本固定的实验 daemon：rootful 与 rootless；先用本目录 `CHECKSUMS.sha256` 校验探针包，复用 13 的 Dockerfile、固定 digest。rootless 所需 UID/GID 映射、network、cgroup 委派必须事先记录，不能在共享宿主开启或修改 daemon。

```sh
docker info --format '{{json .SecurityOptions}} {{.CgroupDriver}}'
docker inspect containers-probe-20 --format '{{.State.Pid}} {{.Config.User}}'
cat /proc/$OWN_HOST_PID/uid_map /proc/$OWN_HOST_PID/gid_map
cat /proc/$OWN_HOST_PID/cgroup
```

对两个 daemon 使用同一自有镜像，比较宿主 daemon PID/UID、应用内外 UID、端口及控制器；清理各自实例。当前仅 `unshare -Ur` 已验证，daemon 对照、资源委派和端口测试全部 `NOT_RUN`。
