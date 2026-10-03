# 10 OCI 布局字节校验

依赖 Python 3（建议 3.11+，使用 `zip(strict=True)`）。先在文章素材目录执行 `sha256sum -c CHECKSUMS.sha256`，再把源码包解压到新建目录；在包目录内执行：

```sh
set -eu
lab=$(mktemp -d ./experiment-10.XXXXXX)
trap 'rm -r -- "$lab"' EXIT
python3 oci_layout.py create "$lab/layout"
python3 oci_layout.py verify "$lab/layout"
cp -a "$lab/layout" "$lab/tampered"
layer=$(python3 -c 'import json,pathlib,sys; root=pathlib.Path(sys.argv[1]); index=json.loads((root/"index.json").read_text()); manifest=json.loads((root/"blobs/sha256"/index["manifests"][0]["digest"].split(":")[1]).read_text()); print(manifest["layers"][0]["digest"].split(":")[1])' "$lab/tampered")
printf x >> "$lab/tampered/blobs/sha256/$layer"
if python3 oci_layout.py verify "$lab/tampered"; then
    echo 'tampered layer unexpectedly passed' >&2
    exit 1
else
    reject_exit=$?
    printf 'tampered_verify_exit=%s\n' "$reject_exit"
    test "$reject_exit" -eq 1
fi
cp -a "$lab/layout" "$lab/index-only"
python3 - "$lab/index-only/index.json" <<'PY'
import json
import pathlib
import sys

index_file = pathlib.Path(sys.argv[1])
index = json.loads(index_file.read_text())
index['manifests'][0]['platform']['architecture'] = 'unknown'
index_file.write_text(json.dumps(index))
PY
python3 oci_layout.py verify "$lab/index-only"
```

`tampered` 层的 `verify` 应返回 1，由 shell 明确断言；最后一次对 `index-only` 的校验反而仍返回 0：它只验证索引所指向的 blob，尚未验证索引元数据是否由可信来源确认。既有 `image-raw.txt` 只含原版布局及压缩层篡改记录，新平台反例的真实命令、输出与清理另记在 `writing-plans/containers/verification/20261003-10-layout/`，不改写旧日志。trap 只清理本次在解压目录创建的工作目录。本布局不含解释器，OCI 运行时执行 `NOT_RUN`，不能把这两个静态反例用作容器启动证据。
