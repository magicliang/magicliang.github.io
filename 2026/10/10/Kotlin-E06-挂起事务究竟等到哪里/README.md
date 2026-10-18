# Kotlin E06 复跑材料

`kotlin-language-E06.tar.gz` 保存累计 JVM 工程与独立 `springTest`（Spring 6.2.11、真实临时 PostgreSQL 16、R2DBC）。不含未通过设备验收的 E01 Android APK，也不包含构建产物或缓存。测试原始 XML、失败记录和页面证据见仓库 `writing-plans/kotlin/verification/E06/`。

```bash
sha256sum -c kotlin-language-E06.tar.gz.sha256
tar -xzf kotlin-language-E06.tar.gz
cd kotlin-language
./gradlew --no-daemon --offline clean test springTest loopbackTest packageTest
```

离线复跑需要 JDK 21、已缓存的 Gradle/Kotlin/Spring/R2DBC 依赖及本机 `/usr/lib/postgresql/16/bin/` 工具；不能用存档里的 XML 替代本机运行。
