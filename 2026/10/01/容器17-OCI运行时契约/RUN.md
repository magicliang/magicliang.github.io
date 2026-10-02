# 17 OCI bundle 与状态

需要专用 Linux VM 的 root shell、固定 runc 版本、Docker、Python 3、iproute2、nsenter、curl 和具有完整 rootfs 的自建 probe-app 镜像。先校验本目录 `CHECKSUMS.sha256`，解压源码包并用 13 的 Dockerfile 创建 `containers-probe:multi`；以下只用可信镜像，不把 10 的“只有脚本”的 layout 当可运行 rootfs。默认 spec 的 TTY、sh 与只读根不能直接满足探针启动，须先完成配置。

```sh
set -eu
test "$(id -u)" -eq 0
OWN_BUNDLE=$(mktemp -d /tmp/containers-17-bundle.XXXXXX)
OWN_RUNC_ROOT=$(mktemp -d /tmp/containers-17-runc.XXXXXX)
export OWN_BUNDLE OWN_RUNC_ROOT
mkdir "$OWN_BUNDLE/rootfs" "$OWN_BUNDLE/state"
chown 65532:65532 "$OWN_BUNDLE/state"
chmod 700 "$OWN_BUNDLE/state"
docker image inspect containers-probe:multi > "$OWN_BUNDLE/image-inspect.json"
OWN_IMAGE_ID=$(docker image inspect containers-probe:multi --format '{{.Id}}')
OWN_EXPORT_ID=$(docker create "$OWN_IMAGE_ID")
docker export --output "$OWN_BUNDLE/rootfs.tar" "$OWN_EXPORT_ID"
docker rm "$OWN_EXPORT_ID"
sha256sum "$OWN_BUNDLE/rootfs.tar"
tar -xpf "$OWN_BUNDLE/rootfs.tar" -C "$OWN_BUNDLE/rootfs"
mkdir -p "$OWN_BUNDLE/rootfs/tmp/containers-state"
runc --version
runc spec --bundle "$OWN_BUNDLE"
python3 - <<'PY'
import json
import os
from pathlib import Path

bundle = Path(os.environ['OWN_BUNDLE'])
path = bundle / 'config.json'
config = json.loads(path.read_text())
config['process']['terminal'] = False
config['process']['args'] = ['/usr/local/bin/python3', '/app/probe_app.py', '--host', '127.0.0.1', '--state-dir', '/tmp/containers-state']
config['process']['cwd'] = '/app'
config['process']['user'] = {'uid': 65532, 'gid': 65532}
config['process']['capabilities'] = {key: [] for key in ('bounding', 'effective', 'inheritable', 'permitted', 'ambient')}
config['root'] = {'path': 'rootfs', 'readonly': True}
config['mounts'].append({'destination': '/tmp/containers-state', 'type': 'bind', 'source': str(bundle / 'state'), 'options': ['bind', 'rw', 'nosuid', 'nodev', 'noexec']})
path.write_text(json.dumps(config, indent=2) + '\n')
PY
sha256sum "$OWN_BUNDLE/config.json"
runc --root "$OWN_RUNC_ROOT" create --bundle "$OWN_BUNDLE" containers-17-own < /dev/null > "$OWN_BUNDLE/app.log" 2>&1
runc --root "$OWN_RUNC_ROOT" state containers-17-own > "$OWN_BUNDLE/created.json"
cat "$OWN_BUNDLE/created.json"
OWN_PID=$(python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); assert s["status"] == "created" and s["pid"] > 0; print(s["pid"])' "$OWN_BUNDLE/created.json")
nsenter --target "$OWN_PID" --net ip link set lo up
cat "/proc/$OWN_PID/cgroup"
cat "/proc/$OWN_PID/mountinfo"
runc --root "$OWN_RUNC_ROOT" start containers-17-own
runc --root "$OWN_RUNC_ROOT" state containers-17-own > "$OWN_BUNDLE/running.json"
cat "$OWN_BUNDLE/running.json"
nsenter --target "$OWN_PID" --net curl --fail --max-time 2 --retry 10 --retry-connrefused --retry-delay 1 --retry-max-time 15 -i http://127.0.0.1:18080/health
nsenter --target "$OWN_PID" --net curl --fail --max-time 2 -i -X POST --data 'only-my-lab' http://127.0.0.1:18080/state
nsenter --target "$OWN_PID" --net curl --fail --max-time 2 -i http://127.0.0.1:18080/state
runc --root "$OWN_RUNC_ROOT" kill containers-17-own KILL
for OWN_WAIT in 1 2 3 4 5 6 7 8 9 10; do
    runc --root "$OWN_RUNC_ROOT" state containers-17-own > "$OWN_BUNDLE/stopped.json"
    if python3 -c 'import json,sys; sys.exit(json.load(open(sys.argv[1]))["status"] != "stopped")' "$OWN_BUNDLE/stopped.json"; then break; fi
    sleep 1
done
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["status"] == "stopped"' "$OWN_BUNDLE/stopped.json"
cat "$OWN_BUNDLE/stopped.json"
runc --root "$OWN_RUNC_ROOT" delete containers-17-own
if runc --root "$OWN_RUNC_ROOT" state containers-17-own > "$OWN_BUNDLE/deleted-state.json" 2> "$OWN_BUNDLE/deleted-state.err"; then exit 1; fi
cat "$OWN_BUNDLE/deleted-state.err"
```

HTTP 请求仅进入该进程的 network namespace，用 VM 的 curl 访问已启用的 loopback；没有发布宿主端口。state 目录通过自有 bind 挂载保持可写，根文件系统仍只读。这里明确用 `KILL` 强制结束实验进程，再最多轮询 10 次等到 `stopped`，不声称优雅退出；超时或任一步失败时停止后续删除，先保存错误并检查本次对象。终止后核对 `deleted-state.err` 确为对象不存在，另查本次进程、挂载与 cgroup 无残留后才删除自建目录。

保留 image inspect 中的 image ID/RepoDigests、导出 tar 摘要（它不是 OCI manifest digest）、config.json、ID、VM 外侧 PID、namespace/cgroup、各步输出、退出码和原始 HTTP 响应。错误 config 只在副本中改，失败后核对相关进程、挂载与目录无残留；共享云端 runc 未安装，正负例 `NOT_RUN`。命令前提参照 [runc v1.3.0 示例配置](https://github.com/opencontainers/runc/blob/v1.3.0/libcontainer/specconv/example.go) 与 [bundle 导出说明](https://github.com/opencontainers/runc/blob/v1.3.0/README.md#creating-an-oci-bundle)。
