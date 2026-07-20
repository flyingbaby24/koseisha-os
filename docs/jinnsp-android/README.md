# JinnSP Android

Capacitor Android shell for JinnSP.

## Build in Android Studio

1. Install Node.js, pnpm, Android Studio, and an Android SDK.
2. From `mobile/jinnsp-android`, run `pnpm install`.
3. Run `pnpm run sync`.
4. Open `mobile/jinnsp-android/android` in Android Studio.
5. Build or run the `app` configuration.

## Debug APK

```powershell
pnpm run apk:debug
```

The APK is generated under `android/app/build/outputs/apk/debug/`.

If PowerShell cannot find Java, install Android Studio's bundled JDK or set `JAVA_HOME`, then reopen the terminal.

## Android features

- `@capacitor/preferences` persists library, folders, playlists, and settings.
- `JinnSPNativePlugin` uses Android Storage Access Framework for audio files, folders, and backup import/export.
- `MediaSessionHelper` publishes playback metadata and Play/Pause/Prev/Next controls to Android notifications and the lock screen.

## Android permissions

- `INTERNET` for R2 and HTTPS direct media playback.
- `POST_NOTIFICATIONS` for Android 13+ playback controls.
- `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_MEDIA_PLAYBACK`, and `WAKE_LOCK` are declared for playback resilience.

## Notes

- Media files are not copied into the app. Android file and folder selections are stored as URI metadata.
- R2 and direct HTTPS media URLs remain playable from the shared Track Library.
- Backup files use the `.jinnsp` extension. CSV remains the editable exchange format.
