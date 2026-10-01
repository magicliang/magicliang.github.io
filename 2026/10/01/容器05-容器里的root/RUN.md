# 05 实验入口

核对 `CHECKSUMS.sha256` 后解包，只使用刚创建的空目录：

```sh
owned=$(mktemp -d /tmp/containers-uid-XXXXXX)
stat -c '%u:%g' "$owned"
unshare -Ur python3 uid_probe.py "$owned"
stat -c '%u:%g' "$owned/owned.txt"
rm -r "$owned"
```

`uid-raw.txt` 保存开始和结束 UTC、真实临时目录、完整命令与每步退出码。预期内部 UID 0 映射为外部 1001，内部可写自己目录；实际一致，最终目录清理为 0。未映射身份拥有的绑定目录拒绝路径尚 `NOT_RUN`：仅在专用 VM 新建不同宿主 UID 的测试目录，记录映射、目录所有者、写入 errno 和目录删除结果；不要向共享宿主系统目录写入。
