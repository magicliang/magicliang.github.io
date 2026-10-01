# 36 Compose/kind 使用同一 digest

专用 VM 中固定 Compose、kind、Kubernetes、镜像仓库版本；先校验本目录源码包、构建完整镜像并记录 `repo@sha256:...`，两端使用相同 digest。`compose.yaml` 只有提供真实 `PROBE_IMAGE` 时才能解析：

```sh
PROBE_IMAGE="$OWN_REGISTRY/probe@sha256:$MANIFEST_SHA256" docker compose -f compose.yaml config
PROBE_IMAGE="$OWN_REGISTRY/probe@sha256:$MANIFEST_SHA256" docker compose -f compose.yaml up -d
PROBE_IMAGE="$OWN_REGISTRY/probe@sha256:$MANIFEST_SHA256" docker compose -f compose.yaml ps
curl -i http://127.0.0.1:18080/ready
```

以自有 Kubernetes Deployment/Service 使用相同 digest，按 UID/容器 ID/PID 记录请求和卷状态；坏版本只在自建项目/namespace 部署，记录失败/回退后响应、数据版本兼容性，再清理自己的 Compose project、kind 对象与卷（确认自有数据可丢弃）。本机无运行时或镜像 digest，全部 `NOT_RUN`。
