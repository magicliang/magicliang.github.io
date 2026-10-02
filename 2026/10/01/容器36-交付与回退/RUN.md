# 36 Compose/kind 使用同一 digest

专用 VM 中固定 Compose、kind、Kubernetes、镜像仓库版本；先校验本目录源码包、构建完整镜像并记录 `repo@sha256:...`，两端使用相同 digest。`compose.yaml` 的变量表达式只检查 `PROBE_IMAGE` 非空，非空标签或占位值也能通过该项检查；真实 digest 与平台需另行核验：

使用更新后源码包构建的镜像，其状态目录在切换至 UID/GID 65532 前已设为 65532:65532、0700。启动 Compose 前先运行 `sh verify_volume.sh "$OWN_REGISTRY/probe@sha256:$MANIFEST_SHA256"`；脚本只验证独立新卷，不迁移 Compose 已有卷。首次 Compose 使用新建空卷与默认复制行为；若复用已有卷，先核对所有权与备份，不能把旧目录权限不匹配当作应用不可用，也不能自动改写其数据。

```sh
PROBE_IMAGE="$OWN_REGISTRY/probe@sha256:$MANIFEST_SHA256" docker compose -f compose.yaml config
PROBE_IMAGE="$OWN_REGISTRY/probe@sha256:$MANIFEST_SHA256" docker compose -f compose.yaml up -d
PROBE_IMAGE="$OWN_REGISTRY/probe@sha256:$MANIFEST_SHA256" docker compose -f compose.yaml ps
curl -i http://127.0.0.1:18080/ready
```

以自有 Kubernetes Deployment/Service 使用相同 digest，按 UID/容器 ID/PID 记录请求和卷状态；坏版本只在自建项目/namespace 部署，记录失败/回退后响应、数据版本兼容性，再清理自己的 Compose project、kind 对象与卷（确认自有数据可丢弃）。目录权限仅完成源码静态检查；本机 HTTP/TERM 回归也不能替代新卷、Compose/kind 与 digest 验证。上述运行时场景须补跑，全部 `NOT_RUN`。
