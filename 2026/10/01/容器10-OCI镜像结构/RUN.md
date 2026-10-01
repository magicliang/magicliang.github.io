# 10 OCI 布局字节校验

依赖 Python 3（建议 3.11+，使用 `zip(strict=True)`）。先在文章素材目录执行 `sha256sum -c CHECKSUMS.sha256`，再把源码包解压到新建目录；在包目录内执行：

```sh
lab=$(mktemp -d /tmp/containers-oci-lab-XXXXXX)
python3 oci_layout.py create "$lab/layout"
python3 oci_layout.py verify "$lab/layout"
cp -a "$lab/layout" "$lab/tampered"
layer=$(python3 -c 'import json,pathlib,sys; root=pathlib.Path(sys.argv[1]); index=json.loads((root/"index.json").read_text()); manifest=json.loads((root/"blobs/sha256"/index["manifests"][0]["digest"].split(":")[1]).read_text()); print(manifest["layers"][0]["digest"].split(":")[1])' "$lab/tampered")
printf x >> "$lab/tampered/blobs/sha256/$layer"
python3 oci_layout.py verify "$lab/tampered"
rm -r "$lab"
```

末次 `verify` 预期返回非零；真实输出与每步退出码在 `image-raw.txt`，篡改后实际退出 1，原样验证返回 0，清理返回 0。本布局不含解释器，OCI 运行时执行 `NOT_RUN`，不能把此演算结果用作容器启动证据。
