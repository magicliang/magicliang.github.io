# 19 同一次启动的证据链

需要专用 VM 的固定 Docker/containerd/runc 版本、与 13 相同的 probe-app 镜像 digest。先在素材目录校验 `CHECKSUMS.sha256`，解压源码并用固定基础 digest 构建。

```sh
docker version
docker image inspect containers-probe:multi --format '{{.Id}} {{json .RepoDigests}}'
docker run -d --name containers-probe-19 -p 127.0.0.1:18080:18080 containers-probe:multi
docker inspect containers-probe-19 --format '{{.Id}} {{.State.Pid}} {{.State.Status}}'
curl -i http://127.0.0.1:18080/ready
docker logs containers-probe-19
docker rm -f containers-probe-19
```

用同一个容器 ID 关联 daemon/运行时的时序与宿主 PID，再在实验镜像副本里用不存在的入口路径做反例。为每条命令保存起止时间、退出码、原始日志和清理情况。共享环境没有 Docker，全部 `NOT_RUN`。
