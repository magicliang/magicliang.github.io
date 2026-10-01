# 00 实验入口与核对

依赖：Linux、Python 3、POSIX shell、curl；执行者仅访问自己的临时目录。`probe-bundle.tar.gz` 是独立源码包；`CHECKSUMS.sha256` 校验其传输内容。

```sh
sha256sum -c CHECKSUMS.sha256
mkdir -p /tmp/containers-00-own-state
sh env_probe.sh
python3 probe_app.py --state-dir /tmp/containers-00-own-state --port 18080 --ready-delay 1
curl -i http://127.0.0.1:18080/identity
curl -i http://127.0.0.1:18080/ready
```

先在文章素材目录执行校验，再在新建目录解压，将 `env_probe.sh` 和 `probe_app.py` 的调用移至该目录；`CHECKSUMS.sha256` 是包的旁挂清单，不在包内。端口已经占用时换自己的闲置端口。预期：探针有 PID、`/health` 成功，就绪前 `/ready` 为 503。实际：见 `env-raw.txt` 和 `probe-raw.txt`，该次实验使用 `--port 0` 分配了临时端口；原始输入、真实端口、退出码和删除目录步骤均保留于日志。预期容器与普通进程的双侧对照当前 `NOT_RUN`，缺 Docker/containerd/runc；专用 VM 上安装固定版本后，用此包为镜像构建上下文，记录 `docker image inspect` digest、`docker inspect` ID/PID，并在宿主和容器两侧读取 `/proc/self/ns/*`。仅删除自己创建的实例，不修改共享 daemon。
