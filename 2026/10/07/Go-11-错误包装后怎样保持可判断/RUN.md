# 11 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

先执行 `sha256sum -c SHA256SUMS`，解包 `go-language-11.tar.gz`，进入 `go-language/` 按 `VERSIONS.md`、`RUN.md` 复跑。包内含截至 11 的完整累计工程、11 当章 Go 实验以及早期章节除 HTTP 下载二进制以外的文本证据；早期 HTTP 原始下载件仍在各章素材。

`unpack-*` 是本章包真实独立解包后的原始命令、环境、双流和退出码。CLI 对文件打不开显示固定描述，错误树仍向本工程内部测试保留 `*os.PathError`；两种边界要分别验证。页面或归档校验通过，不能代替 Go 错误路径实验。
