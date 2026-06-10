# Jarvis Mobile (Android APK)

Обёртка PWA Jarvis в Android-приложение через [Capacitor](https://capacitorjs.com).
Тот же интерфейс, что и в браузере, но как обычное приложение из APK.

## Что нужно один раз
- [Node.js](https://nodejs.org) (есть)
- [Android Studio](https://developer.android.com/studio) (включает Android SDK + JDK)

## Сборка APK
```bash
cd mobile
npm install
npm run add:android      # создаёт android-проект (один раз)
npm run build:apk        # Windows: gradlew.bat assembleDebug
# Linux/macOS: npm run build:apk:linux
```
Готовый файл: `mobile/android/app/build/outputs/apk/debug/app-debug.apk`

Либо открыть проект в Android Studio и нажать Run/Build:
```bash
npm run open:android
```

## Самый простой путь без Android Studio
Если PWA доступна по публичному HTTPS-адресу — загрузите её URL на
[PWABuilder.com](https://www.pwabuilder.com) → он сгенерирует подписанный APK
автоматически. (Для локального сервера это не подойдёт — нужен публичный адрес.)

## Как подключиться
APK не привязан к конкретному ПК: при первом запуске введите адрес сервера
(`http://<IP-компьютера>:8000`) и токен (`AUTH_TOKEN`). Сервер поднимается в
десктопном Jarvis: Настройки → «Запустить сервер для телефона».

> APK ходит на сервер по обычному HTTP в локальной сети — в `capacitor.config.json`
> для этого включены `cleartext` и `allowMixedContent`.
