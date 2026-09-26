# ERP Portal API migration

All **141 enabled API Server Scripts** are native Python modules in
`server_scripts/`; 22 disabled scripts were excluded. Start at
[CATALOG.md](CATALOG.md) to find each file. `catalog.json` records source names,
modification dates, source SHA-256 hashes, inferred inputs and static DocType
references. Local paths are `life_slimming.api.server_scripts.<id>.run`.

## One entry point for Vue pages

```js
import { dataApi } from '../api'
const { message: context } = await dataApi('portal_is_system_manager')
```

`life_portal/src/api/index.js` is the frontend entry point; its endpoint map
accepts known IDs only. `auth.js` holds login, OTP and reset calls. `http.js`
handles session cookies, CSRF, network errors and Frappe response envelopes.
`dataApi` returns the entire envelope because some legacy scripts also use
top-level `data`, `status` or other fields alongside `message`.
All migrated business endpoints use **POST**. The original endpoints were not
overridden or installed as database Server Scripts. File/download APIs need a
blob client when their page is implemented; `dataApi` is the JSON client.

## Conversion details

Each source body is inside its own native `run(**kwargs)` function. There is no
string `exec`, remote proxy, Server Script enablement or database script installer.
`_runtime.py` binds request arguments, restores them even after exceptions, and
registers endpoints with Frappe. Module import does not execute any business code.

These changes are deliberate:

- Direct SQL retains the Server Script `read_sql` guard; it does not gain direct
  SQL write access. Script `frappe.call` retains the whitelisted-call guard.
- `frappe.make_post_request` uses its native integration utility import.
- Five source scripts only defined decorated functions. Native wrappers now call
  those functions and return their result; nested whitelist decorators are removed.
- The translation API reads `life_google_translate_api_key` from local site
  config. The source contained a placeholder. No external credentials were copied.
- Two enabled sources share `create_po_from_indent360`. Both have distinct local
  IDs with stable suffixes; no ambiguous alias silently picks one.
- `get_reference_referral_summary` had no API Method; its new local endpoint
  uses the script name.
- `get_client_transfer_web_details` now requires authentication and Patient read
  permission before reading patient details. Both guest ConVox callbacks retain
  their stored-token and callback-enabled checks.
- All other source business checks and side effects remain. This is a source
  migration, not a full redesign of 141 business APIs.

Scripts which submit/cancel documents, send messages, sync devices or change
configuration retain those behaviors. They were not executed against production
or local business data during validation.

## Local dependencies

Read-only schema inspection found **37 missing statically named DocTypes across
51 APIs**. See [local_schema_report.json](local_schema_report.json). Examples:
Discount Approval Request, Branch Audit, PD Form and CC Worksheet. Dynamic names,
custom fields, fixtures, workflows, accounts, companies and integration settings
still need page-level verification. No missing static DocTypes does not imply
that an API has been proven operational with this site's data.

Local User also lacks `custom_portal_role`; users without that field see only
Home unless they are Administrator/System Manager. No DocTypes, production
records, workflows or integration settings were imported.

## Login and two-step verification

The responsive Vue login is `/life_portal/login`. The flow was checked against
the last commented, redirect-aware login block in ERP Website Script (modified
2026-08-24). The standard `/login` page remains available.

- Credentials go to native `POST /api/method/login`.
- `tmp_id` and `verification` open the OTP screen. HTTP 200 alone is not success.
- Verification sends only `tmp_id` and `otp`, using Frappe's cached credentials,
  native attempt limits, role rules and session creation.
- SMS/Email challenges display five minutes; OTP App displays three minutes,
  matching installed v15 defaults. Frappe remains authoritative on expiry.
- Resend reauthenticates through native login with a UI cooldown. Passwords stay
  in component memory only and are cleared on success, back, reset or unmount.
- Password reset uses the native rate-limited API and generic confirmation.
  Forced password changes accept only this site's `/update-password` route.
  Normal return URLs stay inside `/life_portal/`.
- Existing MSG91 delivery and per-user two-factor bypass hooks are unchanged.

`mysite.local` currently has `enable_two_factor_auth = 0`; setup did not enable
it. Local users therefore sign in directly. OTP was tested with mock responses;
actual delivery needs enabled two-factor settings and configured SMS/email.

## Verification

From `apps/life_slimming`:

```sh
npm run build:portal
../../env/bin/python -B -m unittest discover -s life_slimming/tests -p test_portal_api_migration.py -v
```

Eight unit tests cover all 141 module imports, whitelist/guest/POST metadata,
request isolation, current-user roles, patient permission checks, function-only
scripts, invalid callback tokens, and login configuration. No database required.

The browser suite is `life_portal/tests/login.browser.cjs`; it mocks all login,
OTP and password-reset responses. With the Vite dev server and Playwright on
Node's module path, run `node life_portal/tests/login.browser.cjs`. `CHROME_PATH`
and `PORTAL_URL` override the browser/server. Test tooling is installed in
`/tmp/life-portal-browser`, outside the app's dependencies.

`tools/verify_portal_migration.py <export.json>` compares every converted body
with the inspected export, including multiline string values and the documented
adapters. All 141 passed. `tools/migrate_portal_apis.py` imports an inspected
export; do not rerun it after editing generated modules, because it overwrites
them. Business-output parity and production delivery are not claimed by these
structural and mocked tests.
