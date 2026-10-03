# 14 专用 BuildKit 缓存实验

固定 13 的 `PYTHON_REF`（实际 digest）和 BuildKit 版本，仅使用可销毁的合成密钥。当前没有构建器，缓存/密钥实验 `NOT_RUN`；Dockerfile 静态可读，但不证明过滤生效。

```sh
set -eu
: "${PYTHON_REF:?需要固定且已查询的平台基础镜像 digest}"
printf '%s' "$PYTHON_REF" | grep -Eq '@sha256:[0-9a-f]{64}$' || exit 1
work=$(mktemp -d ../experiment-14.XXXXXX)
trap 'rm -f -- "$work/secret"; rmdir -- "$work"' EXIT
tag="containers-probe:secret-$(date -u +%Y%m%dT%H%M%SZ)-$$"
printf 'synthetic-container-test-only\n' > "$work/secret"
docker build -f Dockerfile.secret --build-arg PYTHON_IMAGE="$PYTHON_REF" --secret "id=synthetic,src=$work/secret" -t "$tag" .
docker history --no-trunc "$tag"
docker image inspect "$tag"
docker image rm "$tag"
```

合成 secret 位于构建 context 的兄弟目录，不让它成为可从 context 的 `COPY` 路径访问的普通文件；该目录也必须是本任务独立工作区的一部分，绝不能借用其他任务的父目录。

保存构建退出码、每步缓存信息和对自有字符串的图层/日志搜索结果；脚本退出时 trap 只清理本次自己的合成 secret 与空目录，成功时删除本次唯一镜像 tag。如果中途构建或检查失败而已经产生该 tag，先保留错误输出，再核对只属于本次的镜像并手动删除，不能批量清理 builder 缓存。在新的空目录复制上下文，修改源码、排除文件、secret 内容逐次构建比较；`required=true` 缺 secret 的失败路径也保存完整错误信息。不要在真实密钥上做博客实验。历史 `/tmp` 路径的旧日志不改写，新复跑不使用固定的 `/tmp/containers-14-own-secret`。
