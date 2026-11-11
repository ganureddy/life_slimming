# Redis read cache for life_slimming: design

- **Date:** 2026-11-11
- **Status:** design approved section by section; awaiting review of this written spec
- **Branch:** `feature/redis-read-cache`
- **Scope:** phase 1 of the Redis layer. CDN and browser caching get their own specs.

## 1. Problem

On 2026-11-11 the portal (`portal.lifescc.com`, 2 vCPU, 3.9 GB RAM) answered even
`/api/method/ping` in 9–13 s. Pages took 11–50 s, and 16–36 requests per minute were
abandoned by clients (nginx 499). MariaDB used most of both CPUs.

Four database indexes added that day brought pages down to about 2.6 s. MariaDB is still
CPU-bound, because the busiest endpoints repeat the same reads on every call:

| Endpoint | Calls per hour | Repeated work per call |
|---|---|---|
| `life_cc_mobile_v18` (DB Server Script) | ~6,200 | role lookup, 2–5 Lead and call queries per read action |
| `life_slimming.api.convox.poll` | ~3,700 | `resolve_lead` phone match (a full Lead regex scan when the number isn't owned) |
| `life_slimming.api.server_scripts.cc_get_leads.run` | ~2,800 | role lookup, `count`, up to 5,000 Lead rows of about 50 fields, User lookup |
| `life_slimming.api.cc_live_tv.snapshot` | ~760 | every Lead touched since the start of the month, unpaginated |

Static `/assets` are already browser-cached for a year. They're 2.4% of requests and out
of scope here.

## 2. Goals and non-goals

**Goals**
- Cut repeated database reads on the four endpoints above using the existing
  Redis cache (`redis_cache`, port 13000, 195 MB, `allkeys-lru`).
- **Freshness rule:** a user's own writes show on their next read. Writes by anyone else
  show within 30 seconds.
- No behaviour change at all until a site_config switch is turned on, and any endpoint can
  be turned off again instantly.

**Non-goals**
- Caching Frappe core APIs (`frappe.client.get_list`, `/api/resource/*`).
- Caching any action that writes, or any authentication, role or permission decision.
- Phase 2 endpoints (`life_stock_fast_requests` / stock dashboard, operations and billing
  pages), CDN and browser caching.

**Success criteria**
- At least 50% of requests on each enabled endpoint answered from the cache (from `cache.stats`).
- Agent screens respond in under about 1 s.
- MariaDB clearly below CPU saturation.
- nginx 499s close to zero.

## 3. Core module: `life_slimming/cache.py`

### 3.1 API

```python
def cached_read(namespace: str, scope: str, args: dict, compute: Callable[[], T]) -> T
def mark_write(user: str | None = None) -> None
def arm_write_tracking() -> None   # before_request hook
def enabled(namespace: str) -> bool
@frappe.whitelist()  # System Manager only
def stats() -> dict
```

- `namespace` names the cached thing, for example `cc_live_tv`, `cc_get_leads` or `mobile_v18.queue`.
- `scope` names who may share the entry (see section 5), for example `all`, a user ID, or
  `agent@x|mgr=1`.
- `args` holds every input that changes the result. It's serialized to canonical JSON
  (sorted keys) and hashed (SHA-1, first 16 hex characters).

### 3.2 Keys

`frappe.cache` adds the site prefix to every key.

| Key | Contents | Expiry |
|---|---|---|
| `life_slimming:rc:<namespace>:<scope>:<argshash>` | `{"t": compute_start_epoch, "z": zlib(pickle(result))}` | `ttl` (default 30 s) |
| `life_slimming:lw:<user>` | epoch of the user's last committed write | `max(120, 2 × ttl)` s, so a stamp always outlives every entry it must invalidate |
| `life_slimming:rc:stats:<namespace>` | hash: `hit`, `miss`, `stale_own_write`, `too_large`, `error`, `compute_ms`, `stored_bytes` | none (small) |

### 3.3 Read algorithm

1. If `enabled(namespace)` is false, return `compute()`.
2. Look up the entry. It's a **hit** only if it exists (Redis expiry enforces the 30 s) **and**
   `entry.t > lw(frappe.session.user)`. A hit increments `hit` and returns the
   decompressed value.
3. Otherwise count `miss`, or `stale_own_write` if the entry existed but is older than the
   user's last write. Record `t0 = time.time()` **before** calling `compute()`, then compute.
4. Compress the result. If the compressed size is at or below `max_entry_bytes`
   (default 1,048,576), store `{t: t0, z: …}` with expiry `ttl`. Otherwise count `too_large`
   and don't store.
5. Return the result.

Stamping `t0` before computing means a write that commits while `compute()` is running
invalidates the result, so the writer is never served data from before their own write.

### 3.4 Configuration (`site_config.json`, re-read on every request)

```json
"life_slimming_cache": {
  "enabled": 0,
  "ttl": 30,
  "max_entry_bytes": 1048576,
  "disabled": [],
  "mobile_native": 0
}
```

- `enabled` is the master switch, off by default. While it's 0, `mark_write` and
  `cached_read` do no Redis work at all.
- `disabled` lists namespaces, or namespace prefixes such as `mobile_v18`, that are turned
  off individually.
- `mobile_native` sends `life_cc_mobile_v18` to the native code (section 5.1).

### 3.5 Failure handling

- Any Redis or unpickle exception in `cached_read` is logged once per worker process,
  counted as `error` where possible, and answered with `compute()`. Caching failures may
  slow the site down but must never make an endpoint fail.
- Exceptions raised by `compute()` propagate unchanged, and nothing is stored.
- Guest sessions bypass the cache.

### 3.6 Deliberately excluded

No lock against many users rebuilding the same entry at once. Shared entries have about
ten concurrent managers, so that duplicate work is cheap.

## 4. Write tracking (how "own edits instant" works)

The code has 149 writes that bypass document hooks (`frappe.db.set_value`, `.db_set`, raw
SQL), so tracking hangs off the **database commit** instead of document events.

`arm_write_tracking()` is added to `before_request` in `hooks.py`:

1. **Arm:** for a logged-in user with caching enabled, add `_before_commit` to
   `frappe.db.before_commit` and `_after_rollback` to `frappe.db.after_rollback`.
2. **`_before_commit`:** add `_after_commit(wrote=frappe.db.transaction_writes > 0)`
   to `frappe.db.after_commit`.
3. **`_after_commit`:** if `wrote`, call `mark_write(user)`, which sets
   `lw:<user> = time.time()` with a `max(120, 2 × ttl)` s expiry. Then re-arm by adding `_before_commit` and
   `_after_rollback` again.
4. **`_after_rollback`:** re-arm by adding `_before_commit`. A rollback clears the commit queues.

**Invariant:** every callback is added only to a queue *other than the one currently being
run*. `CallbackManager.run()` empties its queue, so a callback that re-added itself to that
same queue would loop forever.

Marking happens **after** `COMMIT`, so any read that starts afterwards sees the committed
data, and any entry computed earlier has `t < lw` and counts as stale.

Writes not made by the viewing user aren't marked: ConVox PBX callbacks (Guest), scheduled
jobs, and managers editing an agent's lead. Those appear within 30 s, which matches the
freshness rule.

## 5. Endpoint coverage (phase 1)

These rules apply to every endpoint:
- Authentication, role, module and manager checks run **before** `cached_read`.
- Write actions never call it.
- Fields that depend on the viewer are added **after** the cached part.

### 5.1 `life_cc_mobile_v18`: move into app code, then cache

- **Copy** the DB Server Script `life_cc_mobile_v18` into
  `life_slimming/api/server_scripts/life_cc_mobile_v18.py` as
  `@script_endpoint(allow_guest=False) def run(**kwargs)`. This follows the existing pattern
  (`CATALOG.md`). The script's top-level code becomes the function body, and the action
  branches stay as they are.
- **Route** with `hooks.py`: `override_whitelisted_methods = {"life_cc_mobile_v18":
  "life_slimming.api.server_scripts.life_cc_mobile_v18.run"}`. Frappe applies the override
  before the Server Script lookup (`frappe.handler.execute_cmd`), so the mobile app keeps
  calling the same name.
- **Fall back:** while `mobile_native` is 0, `run()` returns
  `frappe.handler.run_server_script("life_cc_mobile_v18")`, so behaviour matches today exactly.
- **Cached actions:** `queue`, `calls`, `summary`, `live`, `team`, `feed`.
  - namespace: `mobile_v18.<action>`
  - scope: `"<agent>|mgr=<0|1>"`, where `agent` is the effective agent after the manager
    check
  - args: every `form_dict` input the action reads, plus `today`
- **Never cached:** `dial`, `finish`, `sync`, `recording`, `wa_log`, `plan_save`,
  `target_save`, `number`, and every other action.
- Add a row to `CATALOG.md`.

### 5.2 `cc_get_leads.run`

| Mode | Cached | Scope | Args |
|---|---|---|---|
| date range, every `date_mode` | yes | `all` if `can_view_all_leads`, else the user | `from_date, to_date, date_mode, page_size, start, branch, stage` and the paginated flag |
| `phone` | yes | `search` (global for authorized roles, as today) | normalized digits |
| `query` without `detail` | yes | `search` | `query`, `start` |
| `query` with `detail` | **no** | n/a | n/a |

- **Inside the cache:** the message dict, including `rows`, `total`, `truncated`,
  `has_more`, `start`, `scoped_to_owner` and `lead_owner_name`.
- **Outside the cache, live:** the role check, `can_view_all_leads`, and `contact_manager`.
- **Known limit:** non-paginated lists of up to 5,000 rows may exceed `max_entry_bytes`.
  They're then counted as `too_large` and served uncached.

### 5.3 `cc_live_tv.snapshot`

- The returned dict is cached. `timestamp` stays inside the cached value, so it shows when
  the board data was computed.
- namespace: `cc_live_tv`
- scope: `all` for managers, otherwise the user
- args: `today`, `month_start`, `week_start`
- **Behaviour change:** a disabled user can stay on the board for up to 30 s. Until now,
  `enabled` was re-read on every poll.

### 5.4 ConVox lead resolution (read paths only)

- `resolve_lead(event, lookups, cache_reads=False)` gains `cache_reads`. When it's true, the
  owned and global phone lookups go through `cached_read`:
  - namespace: `convox_resolve`
  - scope: the agent's user
  - args: `kind` (`owned` / `global`) and the number
- `poll()` and `history()` pass `cache_reads=True`.
- `sync_event`, the write path that links a call event to a lead, keeps the default `False`
  and always queries fresh.
- **Behaviour change:** on the read screens, a reassigned number can show its previous lead
  for up to 30 s. Update the code comment in `resolve_lead` to say so.

## 6. Observability and the comparison tool

- **`life_slimming.cache.stats()`:** System Manager only. Returns the per-namespace counters,
  and from Redis `INFO`: `used_memory`, `evicted_keys` and `keyspace_hits/misses`.
- **`life_slimming.cache_tools.compare_mobile(agents, actions)`:** run with
  `bench --site … execute`. For each agent and each **read action only**, it runs both the DB
  script and the native code with `frappe.set_user(agent)` and diffs the JSON, ignoring
  `now`/`timestamp` fields.
  - It refuses any action outside the read list.
  - It rolls back at the end.

## 7. Testing

Pure `unittest` tests in `life_slimming/tests/`, using fake `frappe.cache`, `frappe.db`,
`frappe.conf` and `frappe.session` objects. They need no site and never touch the
production database.

- **`test_read_cache.py`**
  - hit and miss
  - expiry
  - own-write staleness, and writes during `compute()`
  - compression round trip
  - the size cap
  - the switches: master, namespace and prefix
  - Redis errors (falls through), `compute()` errors (propagate, not stored)
  - Guest bypass
  - stats counters
- **`test_write_tracking.py`**
  - no writes, so no mark
  - one commit with writes
  - two commits in one request
  - rollback, then write and commit
  - rollback only
  - never adding to the queue that's running
  - disabled, so no work
- **`test_cache_endpoints.py`**
  - scope and arg building for each endpoint
  - write actions and `detail` bypass the cache
  - viewer-specific fields applied after the cached part
  - `mobile_native = 0` delegates to `run_server_script`
- **Mobile move:** a static check that every action branch in the DB script exists in the
  native module. Matching outputs is checked with `compare_mobile` during rollout.

## 8. Rollout and rollback

1. **Deploy** with `enabled: 0` and `mobile_native: 0`. No behaviour change.
2. **Native mobile:** run `compare_mobile` for 3–5 agents and fix any differences, then
   set `mobile_native: 1` with caching still off.
3. **Turn caching on one namespace at a time:** `cc_live_tv` → `cc_get_leads` →
   `mobile_v18` → `convox_resolve`. After each one, check `cache.stats`, MariaDB CPU and the
   nginx 499 rate.
4. **After a week with no problems,** disable the DB Server Script `life_cc_mobile_v18` and
   keep the record.

Rollback takes effect on the next request with no restart:

```bash
bench --site portal.lifescc.com set-config life_slimming_cache '{"enabled": 0}' --parse
```

## 9. Risks

| Risk | Mitigation |
|---|---|
| Cached data shown to the wrong user | Scope is derived only after the live permission checks, and agents get user-scoped entries. Tests cover scope building. |
| Redis memory pressure evicts Frappe sessions | Compression, a 1 MB per-entry cap and short expiries. Expected use is 10–40 MB of 195 MB. `stats` shows `evicted_keys`. |
| The native mobile code drifts from the DB script | Fallback until `compare_mobile` passes, and the DB script stays the reference until it's disabled. |
| Write tracking misses a write path | Commit-level tracking catches every route. A missed case only means the 30 s rule instead of instant. |
| A behaviour change in `resolve_lead` / CC TV | Read paths only, limited to 30 s, and documented in code comments. |
