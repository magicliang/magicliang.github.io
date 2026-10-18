# 05 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

先执行 `sha256sum -c SHA256SUMS`，解包 `go-language-05.tar.gz`，进入归档内 `go-language/` 目录；从 `VERSIONS.md` 核对 Go 1.27.1、源码 tag/SHA 的来源，从 `RUN.md` 取得实际复跑命令。`evidence/00/` 至 `evidence/05/` 是对应章节截至打包时的原始 Go 实验，05 含三种文件输入结果、读/关错误子测试、两个 defer 例子及实验口径修正记录。

`unpack-*` 是本章包实际独立解包后运行的命令、双流、退出码；其结果不会因网页渲染成功而自动变为通过。Linux `/proc/self/fd` 的计数不可用来推断非 Linux 平台上的打开文件数。
