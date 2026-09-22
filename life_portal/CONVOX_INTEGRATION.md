# ConVox integration for the CC dashboard

## Current local configuration — 2026-09-22

Following the user's vendor call, the vendor permits any three-digit dial prefix;
`111` is now configured. Global integration, automatic token retrieval, encrypted
SSO and callbacks are enabled on `mysite.local`. The saved document secret and IV
are used with `php_literal_prefix`, matching the document's PHP example, based on
the user's instruction to use the documented IV. No alternate IV mode was tried.

Dinesh is mapped to portal user `lifescc006@gmail.com` with agent ID `Dinesh`.
Backend checks for that user report no setup issues and confirm click-to-call,
SSO and callback readiness. An encrypted widget-session URL was generated without
exposing its contents. Administrator remains unmapped; sign in as Dinesh to test.
The user reports vendor APIs, callback URLs and embedding support are enabled.
Live vendor SSO acceptance, calls, audio and callback delivery remain untested.
The earlier pending-setup notes below describe the configuration history.

## What you need to do next on the local site

The **Connect your ConVox account** panel means phone setup is incomplete.
It is not a call failure and does not mean that a customer was called.

1. Refresh the CC dashboard with **Ctrl+Shift+R** after this update.
2. Open **System Settings → ConVox integration** using the link in the phone
   panel. Automatic token retrieval and its protected generation key are configured
   locally. Enter the confirmed dial prefix, enable ConVox, and save once ready
   for live testing. The server IP/domain alone is not enough to place calls.
3. Open **Your agent mapping → ConVox agent mapping**. Enable ConVox for your
   portal user and enter the actual ConVox agent ID. Save. Do not use a lead owner's
   name or assume the portal Administrator is a ConVox agent.
4. For encrypted sign-in, ask ConVox to confirm the deployment secret, IV, IV
   interpretation, and the email/username mapped to that agent. Enter the secret
   and IV in **System Settings → ConVox encrypted SSO**, and the mapped email in
   your User account. Enable SSO after those settings are complete.
5. Click **Check again** in the phone panel, connect/sign in, and set your agent
   to **Idle**. Open the intended lead and click **Start Call**.

Enter secrets in the Password fields on the local site. Do not put them in source
code. The subsequently supplied `Token.pdf` documents POST
`https://lifeslimming.deepijatel.in/ConVoxCCS/rest/secureToken`, authenticated with
the vendor-provided `PROD_...` value in the `Access-Token` header. On 2026-09-22,
the user confirmed that its returned `REFRESH_TOKEN` is sent as `Access-Token`
for click-to-call. Automatic token retrieval is now implemented and configured.
Before every new outbound call, the backend requests a current token from
`secureToken`; the vendor returns an existing valid token or a new one. The
returned token is held only in server request memory. This avoids caching against
an unspecified expiry timezone. The local server's live token retrieval was
verified successfully on 2026-09-22 without placing a call. A token failure stops
before sending CALL; a failed/uncertain CALL is never automatically retried.

The click-to-call document contains `"dial_prefix": "11"` in its sample, but
describes the dial prefix as dynamic. This does not confirm that `11` applies to
this deployment. The user has asked ConVox for the actual prefix; it remains unset.

Update: after the user confirmed ConVox's approval of the PDF values, the PDF
secret and IV were saved and verified on `mysite.local`. The secret is stored in
the Frappe Password field. IV interpretation remains unset and SSO remains disabled
pending clarification of the vendor's IV handling. Following explicit approval,
the supplied callback token was saved in its Password field, and all 14 supplied
agent IDs and mapped emails were saved and verified on enabled local User records.
ConVox was enabled for those individual users. Global integration, callbacks and
SSO remain disabled. Token retrieval is ready; the confirmed dial prefix is pending.
Subsequently, the approved Sales User role was assigned and CC/ConVox identity
access was verified for all 14 users. Read-only dashboard reference access was
subsequently completed and verified for Branch, Healthcare Service Unit, Concern
and Healthcare Practitioner through the Call Centre Reference Reader role.
That additional role grants no create/write/delete/export permissions.

Dashboard notification errors, warnings, and success messages now use readable
toasts for at least 10 seconds. Hovering or focusing pauses dismissal; the × button
allows manual dismissal. Lead forms and the phone workspace remain interactive
panels. Browser alerts and Frappe notification dialogs inside the CC dashboard
use the same toast renderer. Phone scripts have content-versioned URLs and load
before dashboard actions to avoid using a cached older bridge after an update.

Implemented from the four supplied vendor documents: Widget Integration (v2,
2025-10-09), Click to Call 4.0.4, Call Popup 4.0.2, and Call Status.
The documents describe protocols and deployment prerequisites; their firewall
commands and sample credentials were not executed or installed.

## Addresses

- Public widget: `https://lifeslimming.deepijatel.in/ConVoxCCS/`
- Click-to-call: `https://lifeslimming.deepijatel.in/ConVoxCCS/rest/api`
- Supplied private server: `192.168.0.193`. The browser uses the HTTPS domain,
  not this private address or the general `/ConVoxCCS/index` page.

## Local installation

From the bench directory, run once per site (safe to repeat):

```sh
bench --site mysite.local execute life_slimming.api.convox_setup.install
```

This adds System Settings/User fields and the ConVox Call Event DocType. It
preserves existing records and does not enable the integration or create agent
accounts. Rebuild the portal with `npm run build` in `life_portal` after UI changes.
The backend worker needs the updated Python modules; restart it through the normal
deployment process if it does not reload changed code.

In **System Settings → ConVox integration**:

1. Confirm the two HTTPS URLs above.
2. Enable **Retrieve calling token automatically**, and set the vendor's `PROD_...`
   value in **ConVox token-generation key** (Password). Configure the confirmed
   default dial prefix. Automatic mode uses the documented `secureToken` endpoint.
   Manual mode can instead use **ConVox access token**, but that value must be
   replaced when it expires. Never use `X-ConVox-Token` as the generation key.
3. Enable the integration when ready.

In each **User → ConVox agent mapping** (administrator-managed):

- Enable ConVox for that user and enter their ConVox agent ID.
- Optionally override the dial prefix and provide their station.
- Each enabled ConVox agent ID must map to exactly one enabled portal User.
- The user also needs an existing CC role (Sales User, Sales Manager,
  Call Center Export, Branch Sales Invoice, or System Manager).

Without SSO, **Open ConVox sign-in** loads the vendor login inside the phone panel.
No ConVox login passwords are collected by LIFE Portal. Agents sign in to ConVox
and set themselves to Idle there. Minimize keeps the iframe alive across portal
navigation; a full browser reload/logout can interrupt the phone session.

## Encrypted SSO

The backend implements AES-256-CBC with PKCS#7 padding, using
`SHA256(secret UTF-8 bytes)` as the 32-byte key. It Base64-encodes the ciphertext
and URL-encodes it as `ExternalUserName`. Secret/access-token Password fields are
read only on the server; they are never sent to the Vue application. The encrypted
SSO URL response has `Cache-Control: no-store`, is held only in component memory,
and the iframe uses `referrerpolicy="no-referrer"`.

**Vendor confirmation is required before enabling SSO.** The PDF describes a
Base64 IV representing 16 bytes, but its PHP sample passes the literal string to
OpenSSL. Set `Confirmed IV interpretation` explicitly:

- `base64`: decode the provided value to exactly 16 bytes.
- `php_literal_prefix`: use the first 16 UTF-8 bytes, matching PHP's handling of
  an overlong literal IV.

Enter the actual deployment secret and IV, not the published sample secret.
The per-user mapped SSO username defaults to their portal User name/email. ConVox
must map that value to the correct agent account. A static CBC SSO value is
replayable under this vendor protocol; no expiry or nonce was invented.

## Click-to-call and notifications

Open a lead's follow-up and click **Start Call**. The embedded CC page sends its
lead ID and a response-correlation ID to the parent portal, which validates the
message's exact origin and frame source. The portal opens the phone panel and
calls the backend click-to-call API when configuration is ready. If the widget
is not open yet, it opens first; an agent who has not signed in must sign in,
set their status to Idle, then click Start Call again. No call is queued for
automatic submission after login. **Call selected lead** in the panel remains
available for leads selected through the summary. The server checks
that the lead belongs to the agent or that the user has a CC manager role, obtains
the phone from the Lead record, validates the number, and calls the documented API.
The agent ID and token cannot be overridden by browser parameters.

Calls use a 20-character reference and an idempotency key. Simultaneous/repeated
requests are guarded server-side. A timeout is reported as an unknown outcome;
it is never automatically retried. Check the vendor phone before another attempt.
The follow-up timer starts only after an accepted API response and is labelled
**Requested**: it measures time since the request, not connected talk time.
Opening a follow-up no longer increments its displayed call count.
**Phone controls** opens the widget and explains how to hang up; the supplied
documents do not define a separate hang-up API. Vendor call controls
(mute/hold/hangup/disposition) remain inside its widget.

Callback records are stored separately; they do not automatically overwrite lead
status or trust ConVox's lead ID as a local Lead identifier. **Find caller in leads**
uses the existing permission-filtered phone search instead. Polling and history
are restricted to the authenticated user's mapped agent, including manager users.
Recording paths are retained as callback metadata; playback/recording downloads
are not exposed by this implementation. Use ConVox MIS for full recording reports.

## Existing API review and local readiness (2026-09-21)

The ERP Portal connector returned all four enabled Server Script records by their
`api_method`. The local `mysite.local` database has no ConVox Server Script records;
it serves their migrated Python equivalents instead:

| Legacy method | Local implementation | Purpose |
| --- | --- | --- |
| `life_convox_api` | `life_slimming.api.server_scripts.life_convox_api.run` | Permission-checked outbound call |
| `life_convox_frontend` | `life_slimming.api.server_scripts.life_convox_frontend.run` | Agent configuration, polling and history |
| `life_convox_call_popup` | `life_slimming.api.server_scripts.life_convox_call_popup.run` | Authenticated incoming/outgoing popup |
| `life_convox_call_status` | `life_slimming.api.server_scripts.life_convox_call_status.run` | Authenticated call outcome metadata |

The Vue phone calls `life_slimming.api.convox` directly. Its configuration and
widget-session methods also provide the encrypted SSO URL. The four legacy scripts
did not implement the widget encryption. Their call payload and callback field
mappings were useful references, but the old frontend history could query other
agents' events, click-to-call lacked ownership/idempotency checks, and callbacks
treated a static secret as an OAuth Bearer token. The local replacements address
these issues. The connected ERP records were inspected, not changed.

Local event storage and settings fields are installed. At inspection, integration,
callbacks and SSO were disabled, and the access token, dial prefix, SSO secret,
IV interpretation and Administrator agent mapping were missing. The phone now
lists the missing settings and provides administrator links to System Settings
and the current User. No credentials or mappings were invented or copied from
documentation examples. Supply deployment values and enable the integration
before attempting a real call.

## Configure ConVox callbacks

Replace `https://YOUR-PUBLIC-LIFE-PORTAL` with this app's publicly reachable HTTPS
origin. These callbacks must reach this local app's deployment, not an unrelated
ERP instance.

- Popup POST: `https://YOUR-PUBLIC-LIFE-PORTAL/api/method/life_slimming.api.server_scripts.life_convox_call_popup.run`
- Status POST: `https://YOUR-PUBLIC-LIFE-PORTAL/api/method/life_slimming.api.server_scripts.life_convox_call_status.run`

Preferred authentication follows the PDFs: create a dedicated Frappe OAuth service
user/client, obtain a valid Frappe OAuth access token, configure that exact user in
`ConVox OAuth service user`, and send `Authorization: Bearer <access_token>`.
Frappe validates token validity/expiry before invoking the callback. Configure token
renewal in the sending integration. Tokens were not generated during implementation.

For vendor installations supporting static headers, an alternative is a separate
strong Password value in `Optional X-ConVox-Token` and the same `X-ConVox-Token`
header in ConVox. This is shared-header authentication, **not OAuth**. Do not send a
static callback secret in the Authorization header: Frappe treats Bearer values as
OAuth tokens and rejects unrecognized tokens before the callback runs.

Set `Content-Type: application/json`. Configure the vendor's dynamic labels using
the exact field casing in the supplied PDFs. Popup requires `agent_id`,
`call_hit_reference_number`, `process_name`, `mobile_number`, `lead_id`,
`entry_date`, `call_type`, and `station`. Status requires `CALL_REFERENCE_ID`,
`MOBILE_NO`, `PROCESS_NAME`, `CALL_DATE`, `USER_ID`, and `CALL_STATUS`; the documented
disposition, duration, queue, recording and follow-up fields are retained when sent.
Use the site's local timezone for timestamps without an offset.

Enable callbacks in System Settings after installing storage and authenticating the
sender. ConVox support must enable its popup/status features and configure the
processes and dynamic status worker described in the PDFs. Callback retries with
identical content are idempotent. Events contain customer phone/call data; restrict
System Manager access and apply the organisation's retention policy to this DocType.

## Vendor-side issue observed

An unauthenticated HEAD request to the supplied widget endpoint on 2026-09-21
returned HTTP 200 with two Permissions-Policy headers:

```text
permissions-policy: geolocation=(), microphone=(), camera=()
permissions-policy: microphone=(self)
```

The restrictive microphone policy can prevent audio even though the parent iframe
explicitly delegates microphone access. ConVox must remove the conflicting deny
policy and allow microphone use in this embedded deployment. Test this with HTTPS,
actual mapped agents, microphone permission, and the supported browser. DNS/TLS,
WebSocket/SIP/RTP connectivity and iframe embedding permissions remain the vendor
and network administrator's deployment work; no firewall changes were made.

## Validation

```sh
/home/life/frappe-bench/env/bin/python -m unittest discover -s tests -p 'test_convox.py' -v
node --test tests/*.test.cjs
npm run build
```

With the local Vite server running on port 5173 and a test Chrome instance exposing
its debugger on port 9222, run `node tests/cc-notifications.browser.cjs` from
`life_portal`. This opens an isolated test tab, mocks API/widget requests, and
checks desktop/mobile calling, alert-to-toast conversion, real 10-second timing,
hover pause, dismissal, and missing setup. It does not place real calls.

Unit tests use fixture credentials and mocked requests/storage. AES output is
compared against the independent OpenSSL CLI in both IV modes. Browser integration
checks stub the vendor iframe and APIs; no real calls are placed. A live calling,
SSO, microphone and vendor callback round-trip test is still required after setup.
