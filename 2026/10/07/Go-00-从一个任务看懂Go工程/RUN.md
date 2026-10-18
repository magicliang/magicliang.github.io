# 00 文章素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

在本目录运行 `sha256sum -c SHA256SUMS`，随后：

```sh
mkdir -p /tmp/go-language-00-unpack
tar -xzf go-language-00.tar.gz -C /tmp/go-language-00-unpack
cd /tmp/go-language-00-unpack/go-language
cat VERSIONS.md
cat RUN.md
GOTOOLCHAIN=local CGO_ENABLED=0 GOMAXPROCS=2 go test -count=1 -v ./...
```

压缩包包含截至 00 的**完整累计工程**与 `evidence/00/` 的原始输出。Go 工具链按 `VERSIONS.md` 自行安装，包内不附带二进制工具链；本机独立解包的命令与结果见同目录 `unpack-check.*`，它不替代读者在目标平台上复跑。
