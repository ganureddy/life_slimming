# LIFE Portal

Separate Vue 3 SPA inside `life_slimming`. Angular remains in `frontend/`.

The 2026-09-20 page migration connects 36 additional menu entries to 35 original
ERP Web Page sources, plus local client-registration and conversion forms.
See [PAGE_MIGRATION.md](PAGE_MIGRATION.md) for source routes, branch-selection
checks, validation and the 14 entries that are also unwired in the original ERP.
Those notes supersede the initial placeholder-only migration boundary below.
Run the local Frappe server alongside Vite: imported pages use authenticated
`/life_portal_module` frames and the local site's APIs.

## Run

From `apps/life_slimming`:

```sh
npm run build:portal
# Open http://mysite.local:8000/life_portal (bench must be running)

npm run dev:portal
# Open http://127.0.0.1:5173/life_portal/
```

Sign in using the local Frappe site. Vite proxies login, API, files, assets and
Desk requests to `127.0.0.1:8000`, selecting `mysite.local`. Session cookies are
shared across ports only when the browser hostname matches; if needed, sign in
through the Vite login link. No credentials for the connected remote ERP are
stored or used by this application.

For a fresh checkout, install only the portal dependencies:

```sh
npm --prefix life_portal ci
npm run build:portal
```

Do not install from the app root to set up Vue: its existing `preinstall` runs
Angular's installer. Existing Angular `dev` and `build` scripts are unchanged.
Node 18.20.8 and the existing locked Vue 3 / Vite 5 dependencies were used.

## Structure

- `src/layouts/PortalLayout.vue`: shared header, navigation and routed content.
- `src/components/PortalSidebar.vue`: grouped menu, filter, collapse and mobile navigation.
- `src/components/AccountDialog.vue`: accessible account/logout dialog.
- `src/pages/HomePage.vue`: native Vue home module launcher.
- `src/pages/ModulePage.vue`: explicit unavailable-page state until a module is migrated.
- `src/pages/NotFoundPage.vue`: unknown route state.
- `src/router/index.js`: history routes under `/life_portal/`.
- `src/data/menu.json`: labels and groups from ERP Web Page `life-portal-home`.
- `src/lib/session.js`: reactive session and menu visibility.
- `src/lib/api.js`: same-origin API requests with CSRF on POST.
- `../life_slimming/api/portal.py`: authenticated session bootstrap.

## Add the next page

Create, for example, `src/pages/AppointmentsPage.vue`. In `src/router/index.js`,
add a page-component map before `routes`:

```js
const pages = {
  appt: () => import("../pages/AppointmentsPage.vue"),
};
```

Replace the mapped module route's `component` with:

```js
component: pages[item.id] || (() => import('../pages/ModulePage.vue')),
```

The existing `appt` menu item already routes to `/life_portal/appt`. For a new
module, add its item to `src/data/menu.json`, then include it in the appropriate
portal role/access configuration. Enforce actual data permissions on the server;
menu visibility and the placeholder's access check are not API authorization.
New page components must also handle denied access and expired sessions.

## Build and deployment

Vite writes **only** `life_slimming/public/life_portal/` and copies its entry to
`life_slimming/www/life_portal.html`. Rebuild before deployment; generated assets
are ignored in Git. Deploy the HTML and assets together. The existing Angular
output and HTML entry are not touched. There is no bench-wide build or migration
required by these source changes. A production worker restart/cache refresh may
be needed for new Python hooks, using the site's normal deployment process.

The Frappe hook maps `/life_portal/<path>` to the SPA, supporting refresh and
browser Back/Forward. The page controller uses a temporary login redirect that
preserves the requested path/query. Older `?view=appt` style links under
`/life_portal/` resolve to the corresponding named route.

## Migration boundary

The reference is ERP Web Page `life-portal-home` (route `/life-home`), read via
the connected ERP Portal on 2026-09-19. Its 54 navigation entries are preserved
without fabricated task/approval counts. Header branding uses the local site's
`/files/logo%20lifew.png` when available, with a LIFE wordmark fallback.

The reference Home embeds separate role-specific dashboard Web Pages and
`home-block` custom HTML blocks. Those dashboards, business APIs, access-control
editor, pinning, and individual module pages are **not migrated in this first
setup**. The native Home is a module launcher. Other routes explicitly show that
the page is not yet available; no remote pages or scripts are executed.

Portal role labels and default menu groups follow the reference. Administrator
and System Manager see all default groups. There is no hardcoded email override
and no automatic Front Office access for users without a configured portal role.
If local `Portal Access Settings` exists and is readable, its `access_config`
provides show/hide/group overrides. Missing settings/custom fields are supported.
Existing authentication and two-factor hooks are retained.

## Verification

- `npm run build:portal`
- `git diff --check`
- Frappe guest `/life_portal/billing?invoice=test`: 302 to login, preserving URL.
- Guest bootstrap API: 403. Existing Angular `/frontend`: 200.
- Browser checks cover menu filtering, history, reload, old query links, 404,
  collapse/mobile layout, role visibility, account dialog and CSRF logout.
  Browser session responses are mocked; validate signed-in local users before
  connecting business data. No remote ERP records are changed by setup/tests.

Vue history routing reference:
https://router.vuejs.org/guide/essentials/history-mode.html

## Login and central APIs

The portal now has its own login at `/life_portal/login`, including password
visibility, Frappe two-factor challenges, resend/expiry, reset and safe return
URLs. Guest portal links redirect here. The standard `/login` remains available.
This supersedes the original setup notes about using only the standard login.

All 141 enabled ERP API Server Scripts have local Python modules. Start with
[the API catalogue](../life_slimming/api/CATALOG.md), and use `dataApi(id, params)`
from `src/api/index.js` in future pages. Read [the migration notes](../life_slimming/api/MIGRATION.md)
for mapping, changes, verification and dependencies. The individual business
page components remain for the next migration stage.

Local 2FA is currently off; setup does not enable it or send test SMS/email.
The schema check found missing DocTypes referenced by 51 APIs. Those dependencies
must be addressed before their pages can use the migrated endpoints.

### Branch Dashboard — live ERP connection

Open `/life_portal/bdash` after signing in to the local portal. Use **Connect ERP
Portal** with your own `portal.lifescc.com` credentials and verification code.
The ChatGPT connector session is separate and cannot authenticate this app.
No API keys, passwords, or production snapshots are bundled into the frontend.

The page follows the remote `branch-command-center` layout inspected on
2026-09-19 (Web Page modified 2026-09-18), with branch/date filters, money summary,
target progress, daily collections, payment breakdown, appointments, pending
balances, employee collections, attendance, source collections and stock.
Today-only figures and current stock/task snapshots are explicitly labelled;
other figures use the selected date range. API row limits are disclosed.
Walk-in editing, full dues recovery, offers and roster planning remain available
through links to the original portal; they are not yet native Vue components.

API entry point: `src/api/branch.js`. Backend: `life_slimming/api/remote_erp.py`.

| Local action (POST) | Remote request | Purpose |
| --- | --- | --- |
| `connect` | POST `login`, GET `frappe.auth.get_logged_user` | Personal ERP sign-in, including OTP |
| `dashboard` | GET `frappe.client.get_list` (Branch), GET `branch_command_center` | Permission-filtered branch selection and live figures |
| `disconnect` | None | Forget this local session's ERP connection |

The gateway uses a fixed HTTPS origin, verifies TLS, disallows redirects, and
keeps remote session cookies in Redis scoped to the local user AND session ID.
Cached connections expire after one hour of inactivity. Disconnect removes the
local cached connection; it does not log out other ERP browser sessions.
Passwords are forwarded only for login and never saved by this integration.
Business requests are reads; the Vue app does not mutate remote records.
A remote permission/session error, timeout, invalid date range or mismatched
branch response does not render invented zero values or stale figures.

Validation: `../../env/bin/python -m unittest life_slimming.tests.test_remote_erp`
from the app directory; browser tests in `tests/branch.browser.cjs` use mocked
ERP responses and test-only credentials. Authenticated production totals still
require a real user's ERP sign-in; they were not verified using the connector.

### Shared API domain

Edit `life_slimming/public/js/portal_config.js` relative to the app root.
`apiBase: ""` uses the current site. Set an HTTPS origin such as
`apiBase: "https://erp.example.com"` to target another API domain. Vue API
calls, Billing uploads, and embedded module requests share this runtime
setting. Refresh the browser and invalidate any asset cache after changing
it; no frontend rebuild is required. `legacyOrigin` only identifies old
exported links and is not the API destination.

Same-origin hosting or a reverse proxy is recommended for Frappe sessions.
A separate API origin requires credentialed CORS, compatible session cookies,
and CSRF tokens for that backend. Embedded pages remain served and
authenticated by the local Frappe site; changing the API domain does not
migrate users, permissions, or the database.

Workspace layout tokens, including `--header-height`, `--sidebar`, spacing,
and colors, are in `src/style.css`. Executable console calls are removed
from portal-owned source and exported page scripts. Production builds also
strip console and debugger statements; existing UI error messages remain.

Checks: `node --test tests/api-config.test.cjs tests/portal-bridge.test.cjs tests/control.test.cjs`.
