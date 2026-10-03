# 36：同一 digest 的交付与配置回退

状态：附件仅经静态检查；Compose、Kubernetes/CSI 的正常交付、故障注入和恢复均为 `NOT_RUN`。没有第二个坏镜像 digest、数据库或快照，本附件也不验证镜像回退、数据迁移或备份恢复。

## 准备与边界

在专用 Linux VM、专用 Kubernetes 集群运行，下载本文全部附件到同一个空目录，并从仓库工作树中的同名素材目录执行。使用 Bash，在同一终端按顺序执行各代码块；失败即停，先保留日志。需要 Docker Compose、kubectl、Python 3、curl、可拉取的自有探针镜像，以及能给 UID/GID 65532 提供可写卷的 CSI StorageClass。kind 默认存储插件不等同于 CSI；需另行安装适用驱动。NetworkPolicy 只有支持它的 CNI 才会执行，本例只验证允许客户端的路径，不证明拒绝规则生效。所有下载内容及日志写入仓库内本任务独占 `.lab-work/36`；不可在共享节点执行 Compose/CSI/Kubernetes 对象操作。

先在实验环境按规范包的 `Dockerfile.single` 构建并推送到自有仓库，固定基础镜像 digest，记录构建日志、平台和产物 manifest。将实际值导出为 `PROBE_IMAGE=仓库/probe@sha256:64位摘要`、`STORAGE_CLASS_NAME=实际存储类`、`C36_CONTEXT=专用集群context`。认证通过实验环境自己的 Docker/节点凭据配置；附件不携带 Secret。多平台 index 还需另外保存两端选中的 manifest，不能直接把 Docker image ID 与 Kubernetes imageID 字符串相等当成验收条件。

```bash
set -euo pipefail
: "${PROBE_IMAGE:?set a real repo@sha256 digest}" "${STORAGE_CLASS_NAME:?set a CSI StorageClass}" "${C36_CONTEXT:?set a dedicated cluster context}"
export PROBE_IMAGE STORAGE_CLASS_NAME
python3 -c 'import os,re; assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}", os.environ["PROBE_IMAGE"]); assert re.fullmatch(r"[a-z0-9][a-z0-9.-]*", os.environ["STORAGE_CLASS_NAME"])'
sha256sum -c CHECKSUMS.sha256
sha256sum -c C36_CHECKSUMS.sha256
C36_WORK_ROOT="$(git rev-parse --show-toplevel)/examples/containers/.lab-work/36"
mkdir -p "$C36_WORK_ROOT"
test ! -L "$C36_WORK_ROOT"
chmod 700 "$C36_WORK_ROOT"
export C36_EVIDENCE="$(mktemp -d "$C36_WORK_ROOT/evidence.XXXXXX")"
mkdir "$C36_EVIDENCE/bundle"
tar -xzf probe-bundle.tar.gz -C "$C36_EVIDENCE/bundle"
cmp compose.yaml "$C36_EVIDENCE/bundle/compose.yaml"
docker version > "$C36_EVIDENCE/docker-version.txt"
docker compose version > "$C36_EVIDENCE/compose-version.txt"
docker info > "$C36_EVIDENCE/docker-info.txt"
docker pull "$PROBE_IMAGE" 2>&1 | tee "$C36_EVIDENCE/pull.txt"
docker image inspect "$PROBE_IMAGE" > "$C36_EVIDENCE/image.json"
sh "$C36_EVIDENCE/bundle/verify_volume.sh" "$PROBE_IMAGE" 2>&1 | tee "$C36_EVIDENCE/new-volume.txt"
```

## Compose：基线、故障、恢复

`compose.yaml` 与包内文件字节一致；它只强制 `PROBE_IMAGE` 非空，前面的格式检查和实际 pull 才进一步核对输入。固定使用 `c36-own` 项目及新空卷。已有同名容器或卷时停止，不能自动清理或修改旧数据。`compose_snapshot` 保存容器标签、挂载、镜像 ID、健康检查历史及端口；每次更换配置后都重新取容器 ID。

```bash
c36_compose() { docker compose -p c36-own -f compose.yaml "$@"; }
c36_bad() { docker compose -p c36-own -f compose.yaml -f c36-bad.compose.yaml "$@"; }
test -z "$(c36_compose ps -aq)"
test -z "$(docker volume ls -q --filter name='^c36-own_containers-state$')"
compose_snapshot() {
  local phase="$1" cid
  cid="$(c36_compose ps -q probe)"
  test -n "$cid"
  docker inspect "$cid" > "$C36_EVIDENCE/compose-$phase.json"
  docker volume inspect c36-own_containers-state > "$C36_EVIDENCE/volume-$phase.json"
  c36_compose exec -T probe python3 -c 'import os; s=os.stat("/tmp/containers-state"); print(os.getuid(), s.st_uid, s.st_gid, oct(s.st_mode & 0o777))' > "$C36_EVIDENCE/owner-$phase.txt"
  curl --fail --silent --show-error --max-time 5 -D "$C36_EVIDENCE/identity-$phase.headers" "http://127.0.0.1:${PROBE_PORT:-18080}/identity" > "$C36_EVIDENCE/identity-$phase.json"
  curl --fail --silent --show-error --max-time 5 -D "$C36_EVIDENCE/state-$phase.headers" "http://127.0.0.1:${PROBE_PORT:-18080}/state" > "$C36_EVIDENCE/state-$phase.json"
}
c36_compose config > "$C36_EVIDENCE/compose-baseline.yaml"
c36_compose up -d --wait --wait-timeout 90 2>&1 | tee "$C36_EVIDENCE/compose-up.txt"
curl --fail --silent --show-error --max-time 5 -D "$C36_EVIDENCE/write.headers" --data-binary 'c36-synthetic-state' "http://127.0.0.1:${PROBE_PORT:-18080}/state" > "$C36_EVIDENCE/write.json"
compose_snapshot baseline
c36_bad config > "$C36_EVIDENCE/compose-bad.yaml"
c36_bad up -d 2>&1 | tee "$C36_EVIDENCE/compose-bad-up.txt"
for attempt in $(seq 1 45); do
  health="$(docker inspect --format '{{.State.Health.Status}}' "$(c36_compose ps -q probe)")"
  test "$health" != unhealthy || break
  sleep 2
done
compose_snapshot bad
printf '%s\n' "$health" > "$C36_EVIDENCE/compose-bad-health.txt"
test "$health" = unhealthy
c36_compose up -d --wait --wait-timeout 90 2>&1 | tee "$C36_EVIDENCE/compose-restore.txt"
compose_snapshot restored
python3 - <<'PY' | tee "$C36_EVIDENCE/compose-check.txt"
import json, os, pathlib
p = pathlib.Path(os.environ['C36_EVIDENCE'])
items = [json.loads((p / f'compose-{phase}.json').read_text())[0] for phase in ('baseline', 'bad', 'restored')]
assert [x['State']['Health']['Status'] for x in items] == ['healthy', 'unhealthy', 'healthy']
assert len({x['Image'] for x in items}) == 1
for x in items:
    assert x['Config']['Image'] == os.environ['PROBE_IMAGE']
    assert x['Config']['Labels']['com.docker.compose.project'] == 'c36-own'
    assert any(m.get('Name') == 'c36-own_containers-state' and m['Destination'] == '/tmp/containers-state' for m in x['Mounts'])
for phase in ('baseline', 'bad', 'restored'):
    assert json.loads((p / f'state-{phase}.json').read_text())['value'] == 'c36-synthetic-state'
print('PASS: Compose config recovery, unchanged image and named volume, HTTP state retained')
PY
```

## Kubernetes：基线

模板包含 Namespace、PVC、Deployment、Service、独立 client Pod 和入口 NetworkPolicy。probe 容器沿用规范镜像 CMD；client 仅执行 Python 等待命令，使用同一 digest，但不挂载状态卷。PVC 的权限取决于实际 CSI 的 fsGroup 支持，不假设镜像目录权限会复制到 PVC。

```bash
k() { kubectl --context "$C36_CONTEXT" --request-timeout=30s "$@"; }
kn() { k -n c36-own "$@"; }
k version -o yaml > "$C36_EVIDENCE/kubernetes-version.yaml"
k get nodes -o json > "$C36_EVIDENCE/nodes.json"
k get storageclass "$STORAGE_CLASS_NAME" -o json > "$C36_EVIDENCE/storageclass.json"
C36_DRIVER="$(k get storageclass "$STORAGE_CLASS_NAME" -o jsonpath='{.provisioner}')"
k get csidriver "$C36_DRIVER" -o json > "$C36_EVIDENCE/csidriver.json"
k get namespace c36-own --ignore-not-found -o name > "$C36_EVIDENCE/existing-namespace.txt"
test ! -s "$C36_EVIDENCE/existing-namespace.txt"
python3 - <<'PY'
import os, pathlib
text = pathlib.Path('c36-k8s.yaml').read_text()
for key in ('PROBE_IMAGE', 'STORAGE_CLASS_NAME'):
    text = text.replace('${' + key + '}', os.environ[key])
assert '${' not in text
(pathlib.Path(os.environ['C36_EVIDENCE']) / 'k8s-rendered.yaml').write_text(text)
PY
k create -f "$C36_EVIDENCE/k8s-rendered.yaml" 2>&1 | tee "$C36_EVIDENCE/k8s-create.txt"
kn rollout status deployment/probe --timeout=90s 2>&1 | tee "$C36_EVIDENCE/k8s-baseline-rollout.txt"
kn wait pod/client --for=condition=Ready --timeout=90s
C36_REVISION="$(kn get deployment probe -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}')"
printf '%s\n' "$C36_REVISION" > "$C36_EVIDENCE/baseline-revision.txt"
k8s_snapshot() {
  local phase="$1" pv
  date -u +%FT%TZ > "$C36_EVIDENCE/k8s-$phase-time.txt"
  kn get deployment,replicaset,pod,service,pvc,networkpolicy -o json > "$C36_EVIDENCE/k8s-$phase.json"
  kn get endpointslice -l kubernetes.io/service-name=probe -o json > "$C36_EVIDENCE/endpoints-$phase.json"
  kn get events -o json > "$C36_EVIDENCE/events-$phase.json"
  pv="$(kn get pvc state -o jsonpath='{.spec.volumeName}')"
  test -n "$pv"
  k get pv "$pv" -o json > "$C36_EVIDENCE/pv-$phase.json"
}
c36_request() {
  kn exec client -- python3 -c 'import json,sys,urllib.request; data=sys.argv[2].encode() if len(sys.argv)>2 else None; r=urllib.request.urlopen(urllib.request.Request(sys.argv[1],data=data),timeout=5); print(json.dumps({"status":r.status,"body":json.load(r)}))' "$@"
}
c36_request http://probe:18080/state c36-synthetic-state > "$C36_EVIDENCE/k8s-write.json"
c36_request http://probe:18080/identity > "$C36_EVIDENCE/k8s-identity-baseline.json"
c36_request http://probe:18080/state > "$C36_EVIDENCE/k8s-state-baseline.json"
k8s_snapshot baseline
kn exec deployment/probe -- python3 -c 'import os; s=os.stat("/tmp/containers-state"); print(os.getuid(), s.st_uid, s.st_gid, oct(s.st_mode & 0o777))' > "$C36_EVIDENCE/k8s-owner.txt"
```

## Kubernetes：readiness 故障与模板恢复

预期现象是新 Pod Running/Ready=false，探针事件出现 404，Service 请求失败，同时容器回环 `/state` 仍成功。`rollout status` 非零可能源自超时以外的错误；只有事件、Pod 和请求共同吻合才算复现。`Recreate` 有停机窗口。负例采证若中止，保留失败现场，并使用已保存的 `baseline-revision.txt` 执行恢复段。

```bash
kn patch deployment probe --type=strategic --patch-file c36-bad-readiness.yaml 2>&1 | tee "$C36_EVIDENCE/k8s-patch.txt"
set +e
kn rollout status deployment/probe --timeout=90s > "$C36_EVIDENCE/k8s-bad-rollout.txt" 2>&1
C36_ROLLOUT_RC=$?
c36_request http://probe:18080/identity > "$C36_EVIDENCE/k8s-bad-service.txt" 2>&1
C36_SERVICE_RC=$?
set -e
printf '%s\n' "$C36_ROLLOUT_RC" > "$C36_EVIDENCE/k8s-bad-rollout.rc"
printf '%s\n' "$C36_SERVICE_RC" > "$C36_EVIDENCE/k8s-bad-service.rc"
k8s_snapshot bad
kn describe pod -l app=c36-probe > "$C36_EVIDENCE/k8s-bad-describe.txt"
kn exec deployment/probe -- python3 -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:18080/state",timeout=5).read().decode())' > "$C36_EVIDENCE/k8s-bad-loopback.json"
test "$C36_ROLLOUT_RC" -ne 0
test "$C36_SERVICE_RC" -ne 0
```

```bash
kn rollout undo deployment/probe --to-revision="$C36_REVISION" 2>&1 | tee "$C36_EVIDENCE/k8s-undo.txt"
kn rollout status deployment/probe --timeout=90s 2>&1 | tee "$C36_EVIDENCE/k8s-restored-rollout.txt"
c36_request http://probe:18080/identity > "$C36_EVIDENCE/k8s-identity-restored.json"
c36_request http://probe:18080/state > "$C36_EVIDENCE/k8s-state-restored.json"
k8s_snapshot restored
python3 - <<'PY' | tee "$C36_EVIDENCE/k8s-check.txt"
import json, os, pathlib
p = pathlib.Path(os.environ['C36_EVIDENCE'])
def read(name): return json.loads((p / name).read_text())
images, claims, handles, pod_uids = [], [], [], []
for phase in ('baseline', 'bad', 'restored'):
    items = read(f'k8s-{phase}.json')['items']
    pods = [x for x in items if x['kind'] == 'Pod' and x['metadata'].get('labels', {}).get('app') == 'c36-probe']
    assert len(pods) == 1, 'wait for old Pod deletion, then capture a new snapshot'
    pod = pods[0]
    pod_uids.append(pod['metadata']['uid'])
    assert pod['status']['phase'] == 'Running'
    assert next(c['status'] for c in pod['status']['conditions'] if c['type'] == 'Ready') == ('False' if phase == 'bad' else 'True')
    status = next(c for c in pod['status']['containerStatuses'] if c['name'] == 'probe')
    assert status['containerID'] and status['imageID']
    images.append(status['imageID'])
    assert pod['spec']['containers'][0]['image'] == os.environ['PROBE_IMAGE']
    claims.append(next(x['metadata']['uid'] for x in items if x['kind'] == 'PersistentVolumeClaim'))
    pv = read(f'pv-{phase}.json')
    handles.append((pv['metadata']['uid'], pv['spec']['csi']['driver'], pv['spec']['csi']['volumeHandle']))
    endpoints = [e for s in read(f'endpoints-{phase}.json')['items'] for e in s.get('endpoints', [])]
    ready = [e for e in endpoints if e.get('conditions', {}).get('ready') is True]
    assert (not ready) if phase == 'bad' else any(e.get('targetRef', {}).get('uid') == pod['metadata']['uid'] for e in ready)
assert len(set(images)) == len(set(claims)) == len(set(handles)) == 1
assert len(set(pod_uids)) == 3
assert any(e.get('involvedObject', {}).get('uid') == pod_uids[1] and 'Readiness probe failed' in e.get('message', '') and '404' in e['message'] for e in read('events-bad.json')['items'])
for phase in ('baseline', 'restored'):
    result = read(f'k8s-state-{phase}.json')
    assert result['status'] == 200 and result['body']['value'] == 'c36-synthetic-state'
assert read('k8s-bad-loopback.json')['value'] == 'c36-synthetic-state'
print('PASS: K8s readiness failure and template recovery, same imageID/PVC/PV handle, Service state retained')
PY
```

若多平台制品调度到不同架构，imageID 一致性断言可能失败；先核对 `nodes.json` 与实际选中 manifest，不能删断言后宣称同字节回退。EndpointSlice 尚未收敛时也应保留原采样，再记录带新时间戳的采样与对应请求，不能覆盖原始证据。

## 停服务并保留数据

完成取证后只停本实验服务，保留 named volume、namespace 和 PVC。没有默认删除卷或 namespace 的命令。确定合成数据可丢弃后，操作者再核对本轮卷身份与 PV reclaimPolicy，单独制定删除动作；Retain 后端需管理员回收。

```bash
c36_compose down 2>&1 | tee "$C36_EVIDENCE/compose-stop.txt"
kn scale deployment/probe --replicas=0 2>&1 | tee "$C36_EVIDENCE/k8s-stop.txt"
kn delete pod client 2>&1 | tee "$C36_EVIDENCE/k8s-client-stop.txt"
docker volume inspect c36-own_containers-state > "$C36_EVIDENCE/retained-compose-volume.json"
kn get pvc state -o json > "$C36_EVIDENCE/retained-pvc.json"
printf 'Evidence: %s\n' "$C36_EVIDENCE"
```

验收时分别填写 Compose/Kubernetes 的正常交付、配置故障和恢复状态，附原始文件路径与退出码。没有执行的分支保持 `NOT_RUN`；checksum、YAML 解析和页面构建都不替代运行结果。

依据：[Compose 合并规则](https://docs.docker.com/reference/compose-file/merge/)、[Deployment 更新和回退](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)、[fsGroup 与卷权限](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)。
