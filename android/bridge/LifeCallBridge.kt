package com.lifescc.app   // Change to the existing APK package.

// Reviewed bridge candidate, 4-Nov-2026. See README_APK_CALLING.md.
// Requires integration and device tests in the actual Android project.

/*
 * LIFE calling bridge candidate — 4 November 2026.
 * Existing LifeApp must delegate dial, getCallLog, uploadRecording,
 * exitApp and openExternal. Forward permission results, onResume and onDestroy.
 * The host Activity must restrict the WebView and all frames to trusted content.
 * Only verified, app-initiated outgoing call rows are exposed to JavaScript.
 * Recordings require one candidate with the full phone number in its filename.
 * Missing permissions/logs/recordings use an explicit approximate/no-audio fallback.
 * Activity/process recreation loses in-memory tracking; do not promise recovery.
 * See README_APK_CALLING.md for manifest, wiring and acceptance checks.
 */

import android.Manifest
import android.app.Activity
import android.content.ContentUris
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.provider.CallLog
import android.provider.MediaStore
import android.telephony.PhoneStateListener
import android.telephony.TelephonyCallback
import android.telephony.TelephonyManager
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.widget.Toast
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.io.DataOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors
import java.util.concurrent.ConcurrentHashMap

class LifeCallBridge(private val activity: Activity, private val web: WebView) {

    companion object {
        const val BASE = "https://portal.lifescc.com"
        const val REQ_CALL = 7101
        val PERMS = mutableListOf(
            Manifest.permission.CALL_PHONE,
            Manifest.permission.READ_CALL_LOG,
            Manifest.permission.READ_PHONE_STATE
        ).apply {
            if (Build.VERSION.SDK_INT >= 33) add(Manifest.permission.READ_MEDIA_AUDIO)
            else add(Manifest.permission.READ_EXTERNAL_STORAGE)
        }.toTypedArray()
    }

    private data class Pending(val callId: String, val tel: String, val startMs: Long, val sid: String = "")

    private val main = Handler(Looper.getMainLooper())
    private val io = Executors.newSingleThreadExecutor()
    private var pending: Pending? = null
    private var queued: Pending? = null           // waiting for permission
    private var sawOffHook = false
    private var listening = false
    private var legacyListener: PhoneStateListener? = null
    private var callback: Any? = null             // TelephonyCallback on API 31+
    private val appCalls = ConcurrentHashMap<String, Pending>()
    private val completed = ConcurrentHashMap<String, JSONObject>()
    private val uploading = java.util.Collections.newSetFromMap(ConcurrentHashMap<String, Boolean>())
    private val uploaded = java.util.Collections.newSetFromMap(ConcurrentHashMap<String, Boolean>())
    private val recordingRequests = java.util.Collections.newSetFromMap(ConcurrentHashMap<String, Boolean>())
    private var endedAt = 0L
    private var requestedPermissions = false
    @Volatile private var closed = false

    // This check is for the main document. The Activity must also block
    // untrusted frames and remove LifeApp before loading untrusted content.
    private fun trustedPage(): Boolean {
        val uri = Uri.parse(web.url ?: return false)
        return uri.scheme == "https" && uri.host == "portal.lifescc.com" &&
            (uri.port == -1 || uri.port == 443)
    }

    private fun runIo(work: () -> Unit) {
        if (closed) return
        try { io.execute { if (!closed) work() } }
        catch (_: java.util.concurrent.RejectedExecutionException) { /* Activity destroyed */ }
    }

    private fun report(message: String) {
        Log.w("LifeCallBridge", message) // no phone numbers, cookies or audio paths
        main.post { if (!closed) Toast.makeText(activity, message, Toast.LENGTH_LONG).show() }
    }

    private fun has(p: String) = activity.checkSelfPermission(p) == PackageManager.PERMISSION_GRANTED
    private fun digits(s: String) = s.filter { it.isDigit() }.takeLast(10)
    private fun sessionId(): String = (CookieManager.getInstance().getCookie(BASE) ?: "")
        .split(";").map { it.trim() }.firstOrNull { it.startsWith("sid=") } ?: ""

    /* ------------------------------------------------------------ dial */
    @JavascriptInterface
    fun dial(tel: String, callId: String) {
        val p = Pending(callId, tel, System.currentTimeMillis(), sessionId())
        main.post {
            if (closed || !trustedPage()) return@post
            if (p.sid.isEmpty() || p.sid != sessionId()) {
                report("Sign in to LIFE before calling"); return@post
            }
            if (!Regex("^\\+?[0-9]{10,15}$").matches(tel) ||
                !Regex("^[A-Za-z0-9_.-]{1,140}$").matches(callId)) {
                report("Invalid call request"); return@post
            }
            if (pending != null || queued != null) {
                report("Finish the current call before dialling again"); return@post
            }
            if (!requestedPermissions && PERMS.any { !has(it) }) {
                requestedPermissions = true
                queued = p
                activity.requestPermissions(PERMS, REQ_CALL)
                return@post
            }
            place(p)
        }
    }

    fun onPermissionResult(rc: Int) {
        if (rc != REQ_CALL) return
        val q = queued ?: return
        queued = null
        if (!closed && trustedPage() && q.sid == sessionId()) place(q)
    }

    private fun place(p: Pending) {
        pending = p.copy(startMs = System.currentTimeMillis(), sid = sessionId())
        // Keep only a day's in-memory work-call metadata.
        appCalls.entries.removeAll { System.currentTimeMillis() - it.value.startMs > 86_400_000 }
        completed.keys.retainAll(appCalls.keys)
        appCalls[p.callId] = pending!!
        completed.remove(p.callId)
        uploaded.remove(p.callId)
        endedAt = 0L
        sawOffHook = false
        try { startListening() }
        catch (_: Exception) { report("Call-state tracking unavailable; timing will be checked on return") }
        try {
            val action = if (has(Manifest.permission.CALL_PHONE)) Intent.ACTION_CALL else Intent.ACTION_DIAL
            activity.startActivity(Intent(action, Uri.fromParts("tel", p.tel, null)))
        } catch (_: Exception) {
            pending = null
            appCalls.remove(p.callId)
            stopListening()
            report("Could not open the phone dialer")
        }
    }

    /* ---------------------------------------------- end-of-call detection */
    private fun startListening() {
        if (listening || !has(Manifest.permission.READ_PHONE_STATE)) return
        val tm = activity.getSystemService(TelephonyManager::class.java) ?: return
        if (Build.VERSION.SDK_INT >= 31) {
            val cb = object : TelephonyCallback(), TelephonyCallback.CallStateListener {
                override fun onCallStateChanged(state: Int) = onState(state)
            }
            tm.registerTelephonyCallback(activity.mainExecutor, cb)
            callback = cb
        } else {
            @Suppress("DEPRECATION")
            val l = object : PhoneStateListener() {
                @Deprecated("Deprecated in Java")
                override fun onCallStateChanged(state: Int, phoneNumber: String?) = onState(state)
            }
            @Suppress("DEPRECATION")
            tm.listen(l, PhoneStateListener.LISTEN_CALL_STATE)
            legacyListener = l
        }
        listening = true
    }

    private fun stopListening() {
        val tm = activity.getSystemService(TelephonyManager::class.java) ?: return
        try {
            if (Build.VERSION.SDK_INT >= 31) (callback as? TelephonyCallback)?.let { tm.unregisterTelephonyCallback(it) }
            else @Suppress("DEPRECATION") legacyListener?.let { tm.listen(it, PhoneStateListener.LISTEN_NONE) }
        } catch (_: Exception) { /* permission may have been revoked */ }
        callback = null; legacyListener = null; listening = false
    }

    private fun onState(state: Int) {
        if (state == TelephonyManager.CALL_STATE_OFFHOOK) sawOffHook = true
        if (state == TelephonyManager.CALL_STATE_IDLE && sawOffHook && pending != null) {
            endedAt = System.currentTimeMillis()
            // the call log row is written a moment after IDLE
            val p = pending
            main.postDelayed({ if (pending == p) finishPending() }, 1500)
        }
    }

    /** Also covers phones where the state callback is missed: called from Activity.onResume */
    fun onResume() {
        val p = pending ?: return
        if (System.currentTimeMillis() - p.startMs > 4000)
            main.postDelayed({ if (pending == p) finishPending() }, 1200)
    }

    @Suppress("DEPRECATION")
    private fun finishPending(attempt: Int = 0) {
        val p = pending ?: return
        // Returning to LIFE while the SIM call is active must not finish it.
        if (has(Manifest.permission.READ_PHONE_STATE)) {
            try {
                if (activity.getSystemService(TelephonyManager::class.java)?.callState !=
                    TelephonyManager.CALL_STATE_IDLE) return
            } catch (_: SecurityException) { return }
        }
        val row = try { findLogRow(p.tel, p.startMs) } catch (_: Exception) { null }
        if (row == null) {
            if (attempt < 10) main.postDelayed({
                if (pending == p) finishPending(attempt + 1)
            }, 2000)
            else {
                // Unknown timing must not be reported as exact Phone Call Log data.
                report("Exact call timing unavailable; LIFE will use approximate timing")
                pending = null
                stopListening()
            }
            return
        }
        pending = null
        stopListening()
        val out = row
        out.put("end", if (endedAt > 0L) endedAt else System.currentTimeMillis())
        out.put("callId", p.callId).put("number", digits(p.tel))
        completed[p.callId] = JSONObject(out.toString())
        // The agent may save the result before Android finishes indexing its log.
        if (recordingRequests.remove(p.callId))
            uploadRecording(p.callId, p.tel, out.optLong("start").toString(), out.optLong("end").toString())
        js("window.LIFE_CALL_DONE&&window.LIFE_CALL_DONE(" + JSONObject.quote(out.toString()) + ")")
    }

    /* ------------------------------------------------------- call log */
    @JavascriptInterface
    fun getCallLog(sinceMs: String): String {
        val since = sinceMs.toLongOrNull() ?: (System.currentTimeMillis() - 3_600_000)
        // Never expose the general call log to JavaScript, including personal calls.
        val arr = JSONArray()
        if (!has(Manifest.permission.READ_CALL_LOG)) return arr.toString()
        completed.values.filter { it.optLong("start") >= since }
            .filter { sessionId().isNotEmpty() && appCalls[it.optString("callId")]?.sid == sessionId() }
            .forEach { arr.put(JSONObject(it.toString())) }
        return arr.toString()
    }

    private fun findLogRow(tel: String, since: Long): JSONObject? {
        val d = digits(tel)
        if (d.length != 10) return null
        // CallLog.DATE is dial time. Do not select an older call to the same lead,
        // or an incoming/personal call made later in the session.
        return queryLog(since - 2000).filter {
            it.optString("number") == d && it.optString("type") == "Outgoing" &&
                kotlin.math.abs(it.optLong("start") - since) <= 5000
        }.minByOrNull { kotlin.math.abs(it.optLong("start") - since) }
    }

    private fun queryLog(since: Long): List<JSONObject> {
        val list = mutableListOf<JSONObject>()
        if (!has(Manifest.permission.READ_CALL_LOG)) return list
        val cols = arrayOf(CallLog.Calls.NUMBER, CallLog.Calls.TYPE, CallLog.Calls.DATE, CallLog.Calls.DURATION)
        activity.contentResolver.query(
            CallLog.Calls.CONTENT_URI, cols, CallLog.Calls.DATE + ">=?", arrayOf(since.toString()),
            CallLog.Calls.DATE + " DESC"
        )?.use { c ->
            while (c.moveToNext() && list.size < 50) {
                val num = digits(c.getString(0) ?: "")
                val type = c.getInt(1)
                val start = c.getLong(2)
                val talk = c.getLong(3)
                val status = when {
                    type == CallLog.Calls.OUTGOING_TYPE && talk > 0 -> "Answered"
                    type == CallLog.Calls.OUTGOING_TYPE -> "Not Answered"
                    type == CallLog.Calls.INCOMING_TYPE -> if (talk > 0) "Answered" else "Not Answered"
                    type == CallLog.Calls.MISSED_TYPE -> "Not Answered"
                    type == CallLog.Calls.REJECTED_TYPE -> "Rejected"
                    else -> "Unknown"
                }
                // Android does not store ring time; estimate = time from dial to answer is not available,
                // so ring is reported 0 and talk is exact (CallLog DURATION = connected seconds).
                list.add(JSONObject().put("number", num).put("start", start).put("talk", talk).put("ring", 0)
                    .put("status", status).put("type", when (type) {
                        CallLog.Calls.OUTGOING_TYPE -> "Outgoing"; CallLog.Calls.INCOMING_TYPE -> "Incoming"; else -> "Missed" }))
            }
        }
        return list
    }

    /* ------------------------------------------------------- recording */
    @JavascriptInterface
    fun uploadRecording(callId: String, tel: String, startMs: String, endMs: String) {
        // Caller-provided timestamps cannot expand recording access.
        val p = appCalls[callId] ?: return
        if (digits(tel) != digits(p.tel)) return
        if (startMs.toLongOrNull() == null || endMs.toLongOrNull() == null) return
        main.post {
            if (closed || !trustedPage() || p.sid.isEmpty() || p.sid != sessionId()) return@post
            val row = completed[callId]
            if (row == null) { recordingRequests.add(callId); return@post }
            if (row.optLong("talk") <= 0 || uploaded.contains(callId) || !uploading.add(callId)) return@post
            // Give the dialer time to close and index the file.
            main.postDelayed({
                if (!closed) runIo {
                    tryUpload(callId, digits(tel), row.optLong("start"), row.optLong("end"), 0)
                }
            }, 6000)
        }
    }

    private fun tryUpload(callId: String, d10: String, s: Long, e: Long, attempt: Int) {
        if (appCalls[callId]?.sid != sessionId()) { uploading.remove(callId); return }
        val file = try { findRecording(d10, s, e) } catch (_: Exception) {
            uploading.remove(callId)
            report("Recording storage is unavailable or permission was denied")
            return
        }
        if (file == null) {
            if (attempt < 3) main.postDelayed({
                if (!closed) runIo { tryUpload(callId, d10, s, e, attempt + 1) }
            }, 20_000)
            else {
                uploading.remove(callId)
                report("No unique recording matched this call; no audio was uploaded")
            }
            return
        }
        main.post {
            if (closed || !trustedPage() || appCalls[callId]?.sid != sessionId()) {
                uploading.remove(callId); return@post
            }
            web.evaluateJavascript("(window.frappe&&frappe.csrf_token)||window.csrf_token||''") { raw ->
                val csrf = try { JSONArray("[" + raw + "]").optString(0) } catch (_: Exception) { "" }
                if (csrf.isEmpty() || csrf == "null") {
                    uploading.remove(callId); report("Recording upload needs a signed-in LIFE session")
                    return@evaluateJavascript
                }
                runIo { upload(callId, file.first, file.second, csrf) }
            }
        }
    }

    /** Fail closed: require the full 10-digit number and one unique candidate.
     * Dialers that hide recordings or omit numbers need a device-specific adapter.
     */
    private fun findRecording(d10: String, s: Long, e: Long): Pair<Uri, String>? {
        val audio = if (Build.VERSION.SDK_INT >= 29) MediaStore.Audio.Media.getContentUri(MediaStore.VOLUME_EXTERNAL)
                    else MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
        val cols = mutableListOf(MediaStore.Audio.Media._ID, MediaStore.Audio.Media.DISPLAY_NAME,
            MediaStore.Audio.Media.DATE_ADDED)
        if (Build.VERSION.SDK_INT >= 29) cols.add(MediaStore.Audio.Media.RELATIVE_PATH)
        val from = (s - 10_000) / 1000
        val to = (e + 120_000) / 1000
        val hits = mutableListOf<Triple<Uri, String, Int>>()
        activity.contentResolver.query(audio, cols.toTypedArray(), MediaStore.Audio.Media.DATE_ADDED + " BETWEEN ? AND ?",
            arrayOf(from.toString(), to.toString()), MediaStore.Audio.Media.DATE_ADDED + " DESC")?.use { c ->
            while (c.moveToNext()) {
                val id = c.getLong(0)
                val name = c.getString(1) ?: ""
                val path = if (Build.VERSION.SDK_INT >= 29) (c.getString(3) ?: "").lowercase() else ""
                val looksLikeCall = path.contains("call") || path.contains("record") || name.lowercase().contains("call")
                val numMatch = d10.length == 10 && name.filter { it.isDigit() }.contains(d10)
                if (!numMatch || !looksLikeCall) continue
                hits.add(Triple(ContentUris.withAppendedId(audio, id), name, (if (numMatch) 2 else 0) + (if (looksLikeCall) 1 else 0)))
            }
        }
        return hits.singleOrNull()?.let { it.first to it.second }
    }

    private fun upload(callId: String, uri: Uri, name: String, csrf: String) {
        try {
            val session = appCalls[callId] ?: error("Call session expired")
            check(!closed && session.sid.isNotEmpty() && session.sid == sessionId())
            val cookies = CookieManager.getInstance().getCookie(BASE) ?: error("No session")
            val boundary = "----life" + System.currentTimeMillis()
            val conn = (URL("$BASE/api/method/upload_file").openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"; doOutput = true; connectTimeout = 20000; readTimeout = 120000
                instanceFollowRedirects = false
                setRequestProperty("Cookie", cookies)
                setRequestProperty("X-Frappe-CSRF-Token", csrf)
                setRequestProperty("Accept", "application/json")
                setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
            }
            val body = try {
              DataOutputStream(conn.outputStream).use { out ->
                fun field(k: String, v: String) {
                    out.writeBytes("--$boundary\r\nContent-Disposition: form-data; name=\"$k\"\r\n\r\n$v\r\n")
                }
                field("is_private", "1")
                field("doctype", "LIFE Mobile Call Log")
                field("docname", callId)
                field("fieldname", "recording")
                val safeName = name.replace(Regex("[^A-Za-z0-9_.-]"), "_").take(120)
                out.writeBytes("--$boundary\r\nContent-Disposition: form-data; name=\"file\"; filename=\"CALL_${callId}_$safeName\"\r\nContent-Type: application/octet-stream\r\n\r\n")
                val input = activity.contentResolver.openInputStream(uri) ?: error("Recording missing")
                input.use { it.copyTo(out) }
                out.writeBytes("\r\n--$boundary--\r\n")
              }
              check(conn.responseCode in 200..299)
              conn.inputStream.bufferedReader().use { it.readText() }
            } finally { conn.disconnect() }
            val fileUrl = JSONObject(body).optJSONObject("message")?.optString("file_url") ?: error("No uploaded file")
            check(fileUrl.startsWith("/private/files/"))
            check(!closed && session.sid == sessionId())
            // link the file to the call row
            val c2 = (URL("$BASE/api/method/life_cc_mobile_v18").openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"; doOutput = true
                instanceFollowRedirects = false; connectTimeout = 20000; readTimeout = 30000
                setRequestProperty("Cookie", cookies); setRequestProperty("X-Frappe-CSRF-Token", csrf)
                setRequestProperty("Content-Type", "application/json"); setRequestProperty("Accept", "application/json")
            }
            try {
                c2.outputStream.use { it.write(JSONObject().put("action", "recording").put("id", callId).put("file_url", fileUrl).toString().toByteArray(Charsets.UTF_8)) }
                check(c2.responseCode in 200..299)
                val result = c2.inputStream.bufferedReader().use { JSONObject(it.readText()) }
                check(result.optJSONObject("message")?.optInt("ok") == 1)
                uploaded.add(callId)
                recordingStatus(callId, "uploaded")
            } finally { c2.disconnect() }
        } catch (_: Exception) {
            report("Recording upload failed; the call remains saved without confirmed audio")
            recordingStatus(callId, "failed")
        } finally { uploading.remove(callId) }
    }

    private fun recordingStatus(id: String, status: String) {
        val payload = JSONObject().put("callId", id).put("status", status)
        js("window.LIFE_RECORDING_STATUS&&window.LIFE_RECORDING_STATUS(" + payload + ")")
    }

    @JavascriptInterface
    fun exitApp() { main.post { if (!closed && trustedPage()) activity.finish() } }

    @JavascriptInterface
    fun openExternal(url: String) {
        main.post {
            if (closed || !trustedPage()) return@post
            val uri = Uri.parse(url)
            val allowed = (uri.scheme == "https" && uri.host == "wa.me") ||
                uri.scheme == "whatsapp" ||
                (uri.scheme == "tel" && Regex("^\\+?[0-9]{10,15}$").matches(uri.schemeSpecificPart))
            if (!allowed) { report("External link is not supported"); return@post }
            try { activity.startActivity(Intent(Intent.ACTION_VIEW, uri)) }
            catch (_: Exception) { report("No app is available to open this link") }
        }
    }

    fun onDestroy() {
        closed = true
        main.removeCallbacksAndMessages(null)
        stopListening()
        pending = null; queued = null
        appCalls.clear(); completed.clear(); uploading.clear(); uploaded.clear(); recordingRequests.clear()
        io.shutdownNow()
    }

    private fun js(code: String) = main.post {
        if (!closed && trustedPage()) web.evaluateJavascript(code, null)
    }
}
