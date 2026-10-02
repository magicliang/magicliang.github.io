# 33：同一 digest 的两套临时公钥

状态：`NOT_RUN`。需要独占实验 registry、可用构建器和已确认版本的 cosign `v2.6.0`；若二进制不是该版本，先核对对应官方帮助/源码并记录差异。本文只给出离线测试密钥验证，不假装集群安装了准入插件。`c33-acceptance.json` 是预测和记录字段清单，**不是**可被 Kubernetes 自动执行的策略。先检查共用源码包与同篇卡片校验，按 13 的步骤从 `probe_app.py` 构建并推送镜像，以实际 immutable manifest digest 填写环境变量；确保正常镜像可拉取且独占镜像仓库允许写入签名附件。

## 一次签名，两个信任锚

以下密钥目录独立于记录目录，实验私钥、口令均不进入文章包或待分享的证据目录；`COSIGN_PASSWORD` 只用于测试，不能拿真实 CI 密钥填它。`cosign generate-key-pair` 在私有目录分别生成 A/B，密码经终端静默输入；不要开启 shell `set -x`。签名禁用透明日志上传、验证显式忽略透明日志，**仅限独占实验**；这种弱化验证绝不能直接照搬到生产策略。

```sh
set -eu
sha256sum -c CHECKSUMS.sha256 C33_CHECKSUMS.sha256
: "${PROBE_IMAGE:?填入已推送至独占 registry 的 manifest digest}"
printf '%s\n' "$PROBE_IMAGE" | grep -Eq '@sha256:[a-f0-9]{64}$'
cosign version
umask 077
OWN_KEYS=$(mktemp -d /tmp/containers-33-keys.XXXXXX)
OWN_EVIDENCE=$(mktemp -d /tmp/containers-33-evidence.XXXXXX)
mkdir "$OWN_KEYS/a" "$OWN_KEYS/b"
read -r -s -p '输入仅用于本次实验的私钥口令: ' COSIGN_PASSWORD
printf '\n'
export COSIGN_PASSWORD
(cd "$OWN_KEYS/a" && cosign generate-key-pair)
(cd "$OWN_KEYS/b" && cosign generate-key-pair)
sha256sum "$OWN_KEYS/a/cosign.pub" "$OWN_KEYS/b/cosign.pub" > "$OWN_EVIDENCE/test-public-key-fingerprints.txt"
date -u +%FT%TZ > "$OWN_EVIDENCE/start-utc.txt"
cosign sign --key "$OWN_KEYS/a/cosign.key" --yes --tlog-upload=false "$PROBE_IMAGE" > "$OWN_EVIDENCE/sign.txt" 2> "$OWN_EVIDENCE/sign.stderr"
cosign verify --key "$OWN_KEYS/a/cosign.pub" --insecure-ignore-tlog "$PROBE_IMAGE" > "$OWN_EVIDENCE/verify-a.txt" 2> "$OWN_EVIDENCE/verify-a.stderr"
```

验证成功也需检查实际输出中 subject digest 是否与 `$PROBE_IMAGE` 精确一致；失败时记录仓库响应、签名查找或密码问题，不能用 `cosign version` 输出代替签名结果。用 B 公钥验证相同 subject，捕获非零退出码和完整错误；若返回 0，说明实验没隔离密钥或验证参数不符合预测，不要写“拒绝通过”。密钥身份必须是本轮不同公钥的指纹，不能只比较文件名。

```sh
if cosign verify --key "$OWN_KEYS/b/cosign.pub" --insecure-ignore-tlog "$PROBE_IMAGE" > "$OWN_EVIDENCE/verify-b.txt" 2> "$OWN_EVIDENCE/verify-b.stderr"; then
  printf 'unexpected_accept\n' > "$OWN_EVIDENCE/verify-b-exit.txt"
else
  printf 'verify-b-exit=%s\n' "$?" > "$OWN_EVIDENCE/verify-b-exit.txt"
fi
date -u +%FT%TZ > "$OWN_EVIDENCE/end-utc.txt"
```

不同 digest 的拒绝**另需**推送真实的第二镜像并保存其 manifest、签名目标和仓库原始记录；向不存在的摘要验证只会混淆镜像缺失和签名不符。SBOM 须固定实际生成器/格式、扫描覆盖范围与扫描库版本后分别保存原始文件与错误；SLSA Provenance v1.0 还要验 subject/builder/materials 及签署者，不通过“有 JSON”判断来源可信。本文没有提供预置签名、SBOM 或 attestation，缺工具/实际构建能力时这三项都保持 `NOT_RUN`。没有实际准入插件时不得报告集群拒绝，`cosign verify` 是终端验证而非 Kubernetes 控制面强制动作。

如需进一步检查运行时，只在自己的 Pod 中用验证过 digest 的镜像读取真实 UID、`/proc/self/status` 中的 Cap/NoNewPrivs 与 `/proc/self/attr/current`，保存 Pod SecurityContext、容器 ID、mountinfo 及原始响应；对照实验需要专用隔离策略，不在共享集群赋予特权或放宽宿主挂载。签名和运行权限是两种独立证据；若没起容器则权限项维持 `NOT_RUN`。

## 私钥清理范围

确认原始退出码和公钥指纹已保存在 `$OWN_EVIDENCE` 后，仅删除**本次创建的两套测试密钥**；若密钥目录混入未知文件，`rmdir` 拒绝并留给操作员处理，不进行递归清空。实验 registry 中创建的签名附件只由 VM 管理者按自己的仓库规则处置，不批量删除镜像或 tag。

```sh
unset COSIGN_PASSWORD
case "$OWN_KEYS" in
  /tmp/containers-33-keys.*) rm -f -- "$OWN_KEYS/a/cosign.key" "$OWN_KEYS/b/cosign.key" "$OWN_KEYS/a/cosign.pub" "$OWN_KEYS/b/cosign.pub" ;;
  *) printf 'refuse unexpected key path\n' >&2; exit 1 ;;
esac
rmdir "$OWN_KEYS/a" "$OWN_KEYS/b" "$OWN_KEYS"
printf 'only public key fingerprints remain in the evidence directory\n'
```

当前无 cosign/镜像 registry/准入与运行时，所有签名、来源、SBOM 和运行权限实验均 `NOT_RUN`，独立校验 JSON 或页面构建不算实际拒绝。
