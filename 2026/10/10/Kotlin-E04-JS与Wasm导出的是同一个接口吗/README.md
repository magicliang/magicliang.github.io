# Kotlin E04 复跑材料

`kotlin-language-E04.tar.gz` 包含原主线 JVM 工程、`shared-model` 的 JVM/JS/Native/Wasm 源码、更新的 npm 锁和复跑脚本，不含 E01 未验收的 Android 工程或任何构建产物。归档 SHA 保存在同名 `.sha256` 文件。

```bash
sha256sum -c kotlin-language-E04.tar.gz.sha256
tar -xzf kotlin-language-E04.tar.gz
cd kotlin-language
PATH=/path/to/node-22/bin:$PATH npm_config_offline=true bash shared-model/verify-js-wasm.sh
./gradlew --offline --no-daemon --console=plain clean test loopbackTest packageTest
```

首次运行需要预先核验并取得 Gradle/Kotlin/Native/LLVM/npm 依赖；离线复跑要求缓存已准备。Linux x86_64、JDK 21、GCC 与 Node 22.23.2 为本次实际实验环境。浏览器、WASI、Wasm Promise 及 Android E01 未运行。
