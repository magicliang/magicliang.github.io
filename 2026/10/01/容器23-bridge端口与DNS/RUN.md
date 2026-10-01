# 23 端口与解析的三条路径

仅在专用 VM 上使用自己的 probe-app 镜像和自己创建的网络，固定 Docker/libnetwork 或选定插件的版本。先校验同名包并解压。记录完整 `ip` 路由/bridge/NAT 规则、监听 socket、conntrack 与 DNS 响应。

```sh
docker network create containers-net-23
docker run -d --name containers-probe-23 --network containers-net-23 -p 127.0.0.1:18080:18080 containers-probe:multi
curl -i http://127.0.0.1:18080/identity
docker inspect containers-probe-23
docker rm -f containers-probe-23
docker network rm containers-net-23
```

负例要在自建网络单独制造监听失败、合成域名解析失败及受限过滤拒绝，每次只改变一个条件；绝不改默认宿主网络。当前无 `ip`/runtime，所有网络运行 `NOT_RUN`。
