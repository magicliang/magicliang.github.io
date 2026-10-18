# 01 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

在此目录先执行 `sha256sum -c SHA256SUMS`，在安装 Go 1.27.1 的环境中解压 `go-language-01.tar.gz`，进入解包所得 `go-language/`，按其中 `RUN.md` 执行。包内同时包含 00 和 01 的原始证据；`stats/` 与根目录的 `main.go` 构成一个 module 下的两个 package，不要只复制 `main.go`。

本机独立解包的运行命令、输出和退出码保存在此目录的 `unpack-*` 文件。对其他平台的构建与全站页面检查另行记账，不能据此冒充实测。
