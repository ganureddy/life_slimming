# LIFE APK calling bridge — reviewed candidate, 4 November 2026

This folder contains a corrected integration candidate, not a built APK.
The Android project/Activity, Gradle configuration and SDK are absent from this
workspace, so compilation, lifecycle integration and phone behavior remain unverified.

## Verified ERP page and API wiring

- Web Page name: `new-mobile-login-testing-kavya`.
- Title: `LIFE APK MOBILE -BHUVAN- V1.2 LIVE`.
- Actual published route: https://portal.lifescc.com/new-mobile-login--testing-kavya
  (two hyphens before `testing`).
- JavaScript version: `2026.11.04-v6.0`.
- Mobile API: `/api/method/life_cc_mobile_v18`.
- Lead-save API: `/api/method/life_slimming.api.server_scripts.cc_update_lead.run`.
- The page already calls `dial`, `getCallLog`, `uploadRecording`, `exitApp`
  and `openExternal` when present. It accepts both object and JSON string call callbacks.
- The old CC test page uses `life_cc_mobile_call`; retain it until the new build
  is accepted. The corrected bridge links recordings through V18.

## Changes in LifeCallBridge.kt

The bridge exposes only completed outgoing rows matched to calls it initiated.
It associates pending permission requests and callbacks with a call, retries delayed
call-log reads, checks the phone state before treating a return to LIFE as completion,
and does not report unavailable timing as exact. Recording uploads require an
app-tracked call, the same signed-in session, positive talk time and one recording
candidate whose filename contains the full 10-digit number. It does not fall back
to a random recording in a matching folder. Ambiguous/missing files are skipped.

The bridge handles missing dialer/permission/storage/network failures, closes HTTP
connections, checks upload/link responses, avoids concurrent duplicate uploads,
queues recording requests that arrive before the call log, and cleans up listeners
and work when destroyed. Failures show a native message; upload/link failures also
emit optional `window.LIFE_RECORDING_STATUS({callId,status})`.
Network upload failures are surfaced, not automatically retried: a timed-out POST
may already have created a file. File-discovery retries are bounded.

## Android integration

Change the package to match the APK. This implementation expects minSdk 23+
and compileSdk 33+; confirm these in the actual project.
Keep the existing LifeApp object and delegate these methods to one bridge instance:

```kotlin
@JavascriptInterface fun dial(tel: String, id: String) = callBridge.dial(tel, id)
@JavascriptInterface fun getCallLog(since: String) = callBridge.getCallLog(since)
@JavascriptInterface fun uploadRecording(id: String, tel: String, start: String, end: String) =
    callBridge.uploadRecording(id, tel, start, end)
@JavascriptInterface fun exitApp() = callBridge.exitApp()
@JavascriptInterface fun openExternal(url: String) = callBridge.openExternal(url)
```

Construct the bridge before loading the page. After the corresponding superclass
calls, forward permission request results to `onPermissionResult(requestCode)`,
Activity resume to `onResume()`, and Activity destruction to `onDestroy()`.
Guard callbacks if the bridge has not yet been initialized. Preserve the existing
Activity back handler: ask `window.LIFE_APP_BACK()` first and respect `handled`;
do not call WebView.goBack() unconditionally.

Add to AndroidManifest.xml:

```xml
<uses-permission android:name="android.permission.CALL_PHONE" />
<uses-permission android:name="android.permission.READ_CALL_LOG" />
<uses-permission android:name="android.permission.READ_PHONE_STATE" />
<uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
<uses-permission android:name="android.permission.INTERNET" />
```

In the existing WebViewClient, intercept `https://wa.me/...`, `whatsapp:`
and `tel:` and delegate to `callBridge.openExternal(url)`, returning true.
Allow only the trusted HTTPS portal to load inside the bridge-enabled WebView.
Remove the interface before loading untrusted content; restrict subframes too.
A main-document URL check cannot authenticate an iframe invoking LifeApp:
[Android bridge security guidance](https://developer.android.com/privacy-and-security/risks/insecure-webview-native-bridges).
Do not override existing login/navigation behavior without checking the Activity.

## Phone limitations and acceptance checks

The native dialer must create recordings and expose them through MediaStore.
Recording availability and filenames vary by phone: a device-specific adapter may
be needed. The safe matcher deliberately skips filenames without the full number.
Talk time comes from the matched call log; ring time is unavailable and stays zero.
The current number matching follows the ERP's India-specific last-ten-digit convention.
If CALL_PHONE is denied, ACTION_DIAL requires the agent to tap Call; delays before
that tap can prevent a safe time match and use approximate timing.
In-memory tracking is lost on Activity/process recreation; durable recovery is
additional Android project work, and unverified recordings are never uploaded.

Test on each supported phone/Android version:

1. Allow permissions; place an answered test call. Compare talk seconds with the
   phone log and verify the result reaches the correct ERP call row.
2. Return to LIFE during a call; ensure no native completion fires while off-hook.
   Test missed callbacks and delayed log indexing.
3. Test unanswered, cancelled and rapid redial calls, including two calls to the
   same number. No prior/incoming call may supply the timing.
4. Deny each permission, cancel the dialer, and revoke permissions in Settings.
   Confirm the call remains usable with an explicit approximate/no-audio fallback.
5. Verify one correct private recording; test missing, ambiguous, inaccessible and
   personal recordings. Confirm no unrelated audio or call rows reach JavaScript/ERP.
6. Test offline upload, expired login, logout/login as another agent, and activity
   destruction. Failures must be visible and old-session data must remain unavailable.
7. Press back twice on the first screen; verify Activity exit. Verify WhatsApp opens
   externally, including when WhatsApp is unavailable.
8. Verify native callbacks arriving after Save update only the matching call; use the
   reviewed mobile-page patch in docs/apk-calling for corrected call/end matching.

Floating lead cards remain optional and are not implemented by this bridge.
Do not request overlay permission unless that feature is actually built.
