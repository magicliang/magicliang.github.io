# 14 专用 BuildKit 缓存实验

固定 13 的 `PYTHON_REF`（实际 digest）和 BuildKit 版本，仅使用可销毁的合成密钥。当前没有构建器，缓存/密钥实验 `NOT_RUN`；Dockerfile 静态可读，但不证明过滤生效。

```sh
printf 'synthetic-container-test-only\n' > /tmp/containers-14-own-secret
docker build -f Dockerfile.secret --build-arg PYTHON_IMAGE="$PYTHON_REF" --secret id=synthetic,src=/tmp/containers-14-own-secret -t containers-probe:secret .
docker history --no-trunc containers-probe:secret
docker image inspect containers-probe:secret
rm -f /tmp/containers-14-own-secret
docker image rm containers-probe:secret
```

保存构建退出码、每步缓存信息和对自有字符串的图层/日志搜索结果；先清理本地自建 secret，再删自己创建的镜像。在新的空目录复制上下文，修改源码、排除文件、secret 内容逐次构建比较；`required=true` 缺 secret 的失败路径也保存完整错误信息。不要在真实密钥上做博客实验。
