# Calling requirements review — 4 November 2026

Reviewed using the ERP Portal connector, not screenshots alone. No remote ERP
records, pages or scripts were changed: the connector exposes reads and workflow
actions, but no document-update or script-execution tool.

## Live state

| Component | Verified source and finding |
|---|---|
| Main mobile page | Web Page `new-mobile-login-testing-kavya`, title `LIFE APK MOBILE -BHUVAN- V1.2 LIVE`, modified 2026-11-04 17:29:45.334556. Published route `new-mobile-login--testing-kavya`; JS version v6.0. |
| Mobile API | Enabled `life_cc_mobile_v18`, modified 2026-11-04 17:12:42.619830. Supports calling, recording, timing, live desktop sync, team and targets. |
| Older mobile API | Enabled `life_cc_mobile_call`, used by the older CC test page. This is a separate version, not proof that the main page uses the wrong API. |
| Lead saves | Main mobile page explicitly calls native `life_slimming.api.server_scripts.cc_update_lead.run`. Local code lacked validate-only handling. |
| CC Dashboard | `cc-new-dash`, modified 2026-11-04 15:50:33.674373. Includes mobile live-call popup and a server-check request carrying `validate_only`. |
| Duplicate API | Enabled Server Scripts `cc_update_lead` and `CC update lead Testing kavya` both register `cc_update_lead`. Their business rules differ. Neither handles validate-only. |
| Test reports | `erp-convox-reports-bhuvan-3nov`, route `branch-visit-report-BhuvanNov3`, modified 2026-11-03 19:40:04.073383. Read for context; no report changes are required by this patch. |
| Lead restoration | `CRM-LEAD-2026-36346` already has Status `Call Back`, CC Sub Status `Callback: Scheduled` and CC Stage `FOLLOW-UP`. No correction needed. |
| Bhargav | Search found `Bhargav Tester`, ConVox disabled and agent ID empty. Confirm identity and obtain the actual ConVox ID before mapping. No user change made. |

The JSON-string callback concern from the initial review is resolved: the live
page already parses both strings and objects. The main page already has exit and
WhatsApp hooks; Kotlin Activity wiring remains necessary.

## Changes prepared here

1. Native `cc_update_lead.py`: after existing access/conflict/status/field checks,
   truthy validate-only requests return `validation_only: 1`, `changed: 0`,
   projected values and the unchanged modified timestamp. They never call save
   hooks or database write methods. Normal saves retain their behavior.
   This validates the endpoint's explicit rules, not every validation/hook that a
   real document save may run.
2. `cc-validation-patches.json`: minimal corresponding patches for both remote
   Server Scripts. Each preserves its existing business policy. This does not
   resolve the duplicate API registration or select which policy should win.
3. `mobile-page-patch.json`: rejects malformed/unidentified completion callbacks,
   rejects old/incoming/unrelated/future call-log matches, and respects actual
   native end timestamps. The reviewed replacement handlers are also saved as
   `mobile-call-handlers.js` for execution tests; do not append that excerpt as a
   second independent module to the live page.
4. `android/bridge/LifeCallBridge.kt`: corrected integration candidate with
   safer app-call/recording association, bounded log/file retries, missing-permission
   fallback, same-session checks, observable failure handling, exit/external-link
   methods and lifecycle cleanup. See its README for exact integration limits.

## Applying the remote patches

Use a target-site bench console with this repository checked out. The helper
compares each reviewed source/version before writing and refuses changed sources.
Review previews first:

```python
from pathlib import Path
root = Path("/path/to/apps/life_slimming")
exec(compile((root / "scripts/console/patch_cc_validation.py").read_text(), "patch_cc_validation.py", "exec"))
patch_cc_validation(root / "docs/apk-calling/cc-validation-patches.json")
patch_mobile_call_page(root / "docs/apk-calling/mobile-page-patch.json")
```

Pass `apply=True` to each function only when ready to install the reviewed result.
The server helper saves both scripts in one transaction. The page helper changes
only the four reviewed JavaScript snippets. Each helper supports repeat execution
and refuses unexpected source changes. The server payload retains the exact old
scripts for rollback through normal ERP change management.

The native Python fix must be deployed through the app's normal deployment
process separately. Patching the Server Script documents alone does not deploy
the native module called explicitly by the mobile page.

Before production acceptance, invoke each relevant endpoint as an authorized
agent with `validate_only=1` and a proposed change, then read the lead again:
status, stage, substatus, modified timestamp and follow-up records must remain
unchanged. Test stale and unauthorized requests too. Do not use the affected real
lead for a normal save test. Android requires an actual project build and the
phone acceptance checks in the bridge README.

## Validation completed

- Six native Python tests: check-only/no writes, stale conflicts, role/status
  protection, disallowed fields, true flags and normal false-flag saves.
- Six installer tests: previews, stale source rejection before any write,
  idempotency and rollback on save failure.
- Five JavaScript execution tests: malformed callbacks, string/object callbacks,
  stale/incoming/unrelated/future rows, actual end time and late call timing.
- Full patched mobile JavaScript and extracted handlers pass `node --check`.
- `git diff --check` passes.
- Kotlin compilation, live ERP endpoint execution and device behavior have not
  been tested. No Android project, compiler or SDK was found in this workspace.

Phone auto-recording/MDM/SIM setup needs device administration. Floating overlays
are optional and remain unimplemented. Old test pages were retained; the request
specified optional deletion after a week, not immediate deletion.
