# LIFE Portal

Separate Vue 3 SPA inside `life_slimming`. Angular remains in `frontend/`.

Current conversion status is tracked page by page in [MIGRATION_PROGRESS.md](MIGRATION_PROGRESS.md). My Tasks / Ticket System now uses a Vue-owned page at `/life_portal/tasks`, preserving its reviewed controller and original markup/styles.

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

### Idle logout exemptions

The portal warns at 57 minutes and logs out after one hour of inactivity by
default. `narendhar@lifescc.com` and `life@gmail.com` are exempt. The server owns
this policy, shared with Frappe Desk and standalone website pages. Override the
list using the site-config key `life_idle_logout_exempt_users` (a JSON list or
comma-separated usernames); an empty list removes all exemptions.

While an app page remains open, exempt accounts send an authenticated heartbeat
at most every 60 seconds, adjusted for shorter Frappe session limits. Other
accounts stop heartbeats after the initial policy check. Explicit logout and
expired sessions still require login. Closing the browser, device sleep, browser
tab suspension, or loss of connectivity can prevent renewal; this is not a
permanent session or automatic re-login.

Deploy the Python and public JS changes, rebuild the portal, clear the site's
cache and restart workers so Desk/website hooks and bootstrap use the policy.
Reload existing tabs after deployment. No production settings are changed by
building locally.

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

### Branch Dashboard

`/life_portal/bdash` now uses the checked-in `branch-command-center` page through
`PortalSourcePage.vue`, the shared module bridge, and the portal page manifest.
The superseded native branch Vue component, styles, and API wrappers were removed.
The remote ERP backend remains available for its other consumers.

### ConVox call details

Open a lead summary or follow-up and choose **ConVox details** beside History.
The modal matches saved events to the lead's mobile (10 digits, +91, or leading 0 formats).
The sidebar also provides **ConVox History** with a Lead ID lookup.
Calls are counted by distinct call reference; all matching events are paginated.
Managers can see all agents; other authorized agents see their own events for
assigned leads. Recordings play when a saved HTTP(S) or Frappe file URL exists;
filenames alone are shown as stored. Raw callback payloads are not exposed.

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

### Legacy source refresh — 13 October 2026

Reviewed all ERP Web Pages updated October 10–13. The active legacy modules now
use the live Stores 360 and CC Visit Report sources; Unjoined Clients is connected
and the Weight Loss source is refreshed. Old Stores and CC Report links remain
portal aliases. See [the source review](../docs/portal-source-review-2026-10-13.md)
for all 18 records, preserved local adapters, API updates and validation limits.

### Native Vue workflow migration

Unjoined Clients, Weight Loss, Cluster Dashboard, Target & Realisation, Price List,
Forms & Documents, and Sales Master now use native Vue components on their menu
routes. Each has desktop/mobile workflow fixtures with mocked APIs. Remaining
legacy screens stay active while their complete native workflow/UI parity is
implemented. See [migration coverage](../docs/vue-migration/README.md) for the
full source inventory, implemented routes and outstanding modules.
