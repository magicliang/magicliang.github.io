# Kotlin E01：工程与设备复跑

`kotlin-language-E01.tar.gz` 包含累计 JVM 工程与独立的 `android-compose/` 探针源代码、Gradle Wrapper；不包含 Android SDK、模拟器镜像、Gradle 缓存、设备 UI XML 或 APK。相应环境、原始日志、页面验收记录见仓库 `writing-plans/kotlin/verification/E01/`。

```bash
sha256sum -c kotlin-language-E01.tar.gz.sha256
tar -xzf kotlin-language-E01.tar.gz
cd kotlin-language
./gradlew --no-daemon --offline clean test
ANDROID_HOME=/path/to/android-sdk ./gradlew -p android-compose --no-daemon --offline assembleDebug
ANDROID_HOME=/path/to/android-sdk E01_EVIDENCE=/tmp/kotlin-e01-device-logs bash android-compose/verify-device.sh
```

JVM 回归需 JDK 21、已缓存的 Kotlin/Gradle 依赖；Android APK 构建另需 platform/build-tools 35、已缓存的 AGP/Compose/Lifecycle 依赖。设备脚本还需已启动并可交互的模拟器或真机。没有设备只能复跑构建，`STOP`/Flow 取消、按钮点击与旋转恢复为 **NOT_RUN**；退出码和断言应保存在另建的证据目录，不以本次博客的日志替代本机结果。
