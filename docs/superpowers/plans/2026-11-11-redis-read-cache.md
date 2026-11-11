# Redis read cache: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve repeated reads on the four busiest life_slimming endpoints from Redis, under
the rule "own writes instant, others' writes within 30 s". Everything stays off until a
site_config switch is turned on.

**Architecture:** One module, `life_slimming/cache.py`, holds `cached_read()`,
commit-based write tracking, the settings, and the stats. Each endpoint keeps its
permission checks live and passes only its data-fetching part to `cached_read()`. The
`life_cc_mobile_v18` DB Server Script moves into app code behind
`override_whitelisted_methods`, and falls back to the DB script until `mobile_native` is on.

**Tech stack:** Frappe 15.109.0, Python 3.12, Redis (`frappe.cache`), stdlib only (`zlib`,
`pickle`, `hashlib`, `json`, `time`), and `unittest` with fakes. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-11-redis-read-cache-design.md`. Read it before
starting any task.

## Global constraints

- **Repo and branch:** the worktree `/home/admin/frappe-bench/worktrees/life_slimming-redis-cache`,
  branch `feature/redis-read-cache`. Never edit `/home/admin/frappe-bench/apps/life_slimming`
  (the live checkout). Never push.
- **Run tests with:**
  `cd /home/admin/frappe-bench/worktrees/life_slimming-redis-cache && /home/admin/frappe-bench/env/bin/python -m unittest <module> -v`.
  The worktree package is imported first. Tests never touch a site or the database.
- **Test style:** follow `life_slimming/tests/test_session_policy.py`: `unittest.TestCase`,
  `frappe.local.conf = frappe._dict()` in `setUp`, and `frappe.destroy()` in `tearDown`.
- **Settings key:** `life_slimming_cache`. Defaults:
  `{"enabled": 0, "ttl": 30, "max_entry_bytes": 1048576, "disabled": [], "mobile_native": 0}`.
- **Key formats** (`frappe.cache` adds the site prefix):
  - entry: `life_slimming:rc:<namespace>:<scope>:<argshash>`
  - stamp: `life_slimming:lw:<user>`
  - stats: `life_slimming:rc:stats:<namespace>`
- **Expiries:** an entry expires after `ttl`. A stamp expires after `max(120, 2 * ttl)` seconds.
- **`argshash`:** `hashlib.sha1(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()[:16]`.
- **Entry value:** `{"t": <compute-start epoch>, "z": zlib.compress(pickle.dumps(result))}`.
  - It's a hit only if `t > lw(user)`, strictly greater.
  - It's stored only if `len(z) <= max_entry_bytes`.
- **Namespaces (exact):** `cc_live_tv`, `cc_get_leads`, `convox_resolve`, and
  `mobile_v18.<action>` for `<action>` in `queue, calls, summary, live, team, feed`.
- **Stats fields (exact):** `hit`, `miss`, `stale_own_write`, `too_large`, `error`, `compute_ms`, `stored_bytes`.
- **Commits:** commit messages end with the line
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review focus

These are inputs the spec implies that no task's own tests would otherwise exercise. Each
one has a test in Task 1.

1. **Settings stored as a JSON string,** for example from `bench set-config` without
   `--parse`, or malformed: parse a JSON string, treat anything unparsable as all
   defaults (caching off), and never raise.
2. **`compute()` returns `None`, `[]` or `{}`:** it's cached and served as a hit, not
   recomputed on every call.
3. **A caller changes the result it got back:** for example `cc_get_leads` sets
   `contact_manager`. The next read must not see that change, because every read
   unpickles a fresh copy.
4. **An entry made in the same instant as a write** (`t == lw`) is stale.
5. **Args containing dates, `frappe._dict` or keys in a different order:** the same
   values give the same key, and different values give different keys.

---

### Task 1: Core read cache, settings and stats

**Files:**
- Create: `life_slimming/cache.py`
- Create: `life_slimming/tests/cache_fakes.py`
- Test: `life_slimming/tests/test_read_cache.py`

**Interfaces:**
- Produces, in `life_slimming.cache`:
  - `CONFIG_KEY = "life_slimming_cache"`
  - `settings() -> frappe._dict`: defaults merged with config (accepts a dict or a JSON string)
  - `enabled(namespace: str) -> bool`: `False` if the master switch is off, or if `namespace`
    or any dotted prefix of it is in `disabled`
  - `cached_read(namespace: str, scope: str, args: dict, compute: Callable[[], Any]) -> Any`
  - `stamp(user: str) -> float`: the last-write epoch, or `0.0`
  - `_now() -> float`: wraps `time.time()`; tests patch it
  - `@frappe.whitelist() stats() -> dict`:
    `{"namespaces": {ns: {field: int}}, "redis": {"used_memory", "evicted_keys", "keyspace_hits", "keyspace_misses"}}`,
    callable by System Manager only (`frappe.only_for("System Manager")`)
- Produces, in `life_slimming.tests.cache_fakes`:
  - `FakeCache`: dict-backed; `get_value`, `set_value(key, val, expires_in_sec=None)`,
    `delete_value`, `make_key`, `hincrby`, `hgetall`, `get_keys(prefix)`, `info()`.
    Expiry uses `clock()`. It can be told to raise on every call (`fail = True`).
  - `FakeClock`: `now: float` and `advance(seconds)`
  - `FakeDB`: Task 2 adds it

- [ ] **Step 1: Write the failing tests** in `test_read_cache.py`. Patch `frappe.cache`
  with `FakeCache` (`patch.object(frappe, "cache", fake)`), `cache._now` with `FakeClock`,
  and set `frappe.local.session = frappe._dict(user="agent@x")`.
  - `test_disabled_by_default_calls_compute_every_time`: two reads mean two computes, and
    `fake` stays empty.
  - `test_hit_within_ttl_and_miss_after`: with `enabled 1`, read twice and get one compute.
    After `clock.advance(31)`, the next read computes again.
  - `test_own_write_makes_entry_stale`: read, set the stamp for `agent@x` to `now + 1`,
    advance 1 s, read again. That's 2 computes, and `stats["stale_own_write"] == 1`.
  - `test_other_users_write_does_not_invalidate`: the stamp for `other@x` does nothing.
  - `test_write_during_compute_invalidates`: `compute` itself sets the stamp to `now`.
    The next read recomputes.
  - `test_equal_timestamps_are_stale` (review focus 4).
  - `test_falsy_results_are_cached`: `None`, `[]` and `{}` each compute once (review focus 2).
  - `test_returned_values_are_independent_copies` (review focus 3).
  - `test_args_hash_stable_and_distinct`: `{"b": 1, "a": date(2026, 11, 11)}` and the same
    values with the keys reversed give the same key. `a = date(2026, 11, 12)` gives a
    different key (review focus 5).
  - `test_too_large_not_stored`: with `max_entry_bytes: 10`, the result is returned and
    not stored, and `too_large == 1`.
  - `test_namespace_and_prefix_disable`: `disabled: ["mobile_v18"]` turns off
    `mobile_v18.queue` but not `cc_live_tv`.
  - `test_settings_accepts_json_string_and_survives_garbage` (review focus 1).
  - `test_redis_failure_falls_through`: with `fake.fail = True`, the result is still
    returned and nothing is raised.
  - `test_compute_exception_propagates_and_is_not_stored`
  - `test_guest_bypasses_cache`
  - `test_stats_requires_system_manager_and_reports_counters`: patch `frappe.only_for`
    to raise and expect the error. Unpatched, the returned dict contains the counters.

- [ ] **Step 2: Run the tests to see them fail.** Run
  `… -m unittest life_slimming.tests.test_read_cache -v`. Expected: an ImportError
  (`life_slimming.cache` doesn't exist yet).

- [ ] **Step 3: Implement `life_slimming/cache.py` (core) and `cache_fakes.py`** following
  spec §3.3.
  - Always reference `frappe.cache` at call time, never `from frappe import cache`.
  - Increment stats with `frappe.cache.hincrby(frappe.cache.make_key(stats_key), field, n)`.
  - Log Redis errors once per process, using a module-level flag and `frappe.log_error`
    wrapped in `try`.

- [ ] **Step 4: Run the tests to see them pass.** Same command. Expected: `OK`, 16 tests.

- [ ] **Step 5: Commit**

```bash
git add life_slimming/cache.py life_slimming/tests/cache_fakes.py life_slimming/tests/test_read_cache.py
git commit -m "feat(cache): add Redis read cache with per-user write staleness"
```

### Task 2: Commit-based write tracking

**Files:**
- Modify: `life_slimming/cache.py`
- Modify: `life_slimming/hooks.py:253-256` (the `before_request` list)
- Modify: `life_slimming/tests/cache_fakes.py` (add `FakeDB`)
- Test: `life_slimming/tests/test_write_tracking.py`

**Interfaces:**
- Consumes: `settings()`, `_now()` and `stamp()` from Task 1.
- Produces:
  - `mark_write(user: str | None = None) -> None`: sets the stamp to `_now()` with expiry
    `max(120, 2 * ttl)`. It does nothing when disabled or for Guest.
  - `arm_write_tracking() -> None`: the `before_request` hook.
- `FakeDB` has the attributes `transaction_writes`, `before_commit`, `after_commit`,
  `before_rollback` and `after_rollback`. Each queue is a `GuardedCallbackManager`, which
  subclasses `frappe.utils.CallbackManager` and **raises `AssertionError` if `add()` is
  called on a queue while it is running**. `write()` increases `transaction_writes`.
  `commit()` and `rollback()` copy `frappe/database/database.py:1173-1201` exactly:
  - `commit()`: reset both rollback queues, run `before_commit`, set
    `transaction_writes = 0`, then run `after_commit`.
  - `rollback()`: reset both commit queues, run `before_rollback`, set
    `transaction_writes = 0`, then run `after_rollback`.

- [ ] **Step 1: Write the failing tests.** Patch `frappe.db` with `FakeDB`, set
  `enabled: 1` and session user `agent@x`, and call `arm_write_tracking()` first.
  - `test_commit_without_writes_does_not_mark`
  - `test_commit_with_writes_marks_after_commit`: assert the stamp equals the clock value
    *at* the `after_commit` stage.
  - `test_two_commits_in_one_request_both_mark`
  - `test_rollback_then_write_commit_marks`
  - `test_two_rollbacks_then_write_commit_marks`
  - `test_never_adds_to_running_queue`: run each sequence above under the guard, with no
    `AssertionError`.
  - `test_disabled_or_guest_does_not_arm`: all queues stay empty.

- [ ] **Step 2: Run the tests to see them fail.** Run
  `… -m unittest life_slimming.tests.test_write_tracking -v`. Expected: an AttributeError
  for `arm_write_tracking`.

- [ ] **Step 3: Implement write tracking in `cache.py` with this callback chain.** Each
  function adds only to queues that aren't running at the time:

```python
def _arm(user):        frappe.db.before_commit.add(lambda: _before_commit(user)); frappe.db.before_rollback.add(lambda: _before_rollback(user))
def _before_commit(u): w = frappe.db.transaction_writes > 0; frappe.db.after_commit.add(lambda: _after_commit(u, w))
def _after_commit(u, w): (mark_write(u) if w else None); _arm(u)
def _before_rollback(u): frappe.db.after_rollback.add(lambda: _arm(u))
```

  Append `"life_slimming.cache.arm_write_tracking"` to `before_request` in `hooks.py`.

- [ ] **Step 4: Run the tests to see them pass.** Run the Task 1 and Task 2 modules.
  Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add life_slimming/cache.py life_slimming/hooks.py life_slimming/tests/cache_fakes.py life_slimming/tests/test_write_tracking.py
git commit -m "feat(cache): mark user writes after each successful commit"
```

### Task 3: Cache `cc_live_tv.snapshot`

**Files:**
- Modify: `life_slimming/api/cc_live_tv.py`
- Test: `life_slimming/tests/test_cache_endpoints.py`

**Interfaces:**
- Consumes: `cache.cached_read`.
- Produces: `_tv_cache_key(user: str, scoped: bool, today: str, month_start: str, week_start: str) -> tuple[str, str, dict]`,
  which returns `("cc_live_tv", user if scoped else "all", {"today": …, "month_start": …, "week_start": …})`.

- [ ] **Step 1: Write the failing tests.**
  - `test_tv_key_scopes_managers_to_all_and_agents_to_self`
  - `test_tv_snapshot_runs_permission_checks_before_cache`: patch `require_module` to raise
    `PermissionError`. Assert `cached_read` is never called.

- [ ] **Step 2: Run the tests to see them fail.** Run
  `… -m unittest life_slimming.tests.test_cache_endpoints -v`. Expected: an ImportError or
  AttributeError for `_tv_cache_key`.

- [ ] **Step 3: Implement.** Move everything after the date calculations into a local
  `compute()` that returns the current dict, and return
  `cache.cached_read(*_tv_cache_key(...), compute)`. Replace the comment "Read enabled
  state on every poll…" with a note that a disabled user can stay on the board for up to
  `ttl` seconds (spec §5.3).

- [ ] **Step 4: Run the tests to see them pass.** Same command. Expected: `OK`.

- [ ] **Step 5: Commit**: `feat(cache): cache CC TV snapshot per manager/agent scope`

### Task 4: Cache `cc_get_leads.run`

**Files:**
- Modify: `life_slimming/api/server_scripts/cc_get_leads.py`
- Test: `life_slimming/tests/test_cache_endpoints.py`

**Interfaces:**
- Consumes: `cache.cached_read`.
- Produces: `_cache_plan(fd: dict, user: str, can_view_all: bool) -> tuple[str, str, dict] | None`.

| Mode | Return value |
|---|---|
| `query` + `detail` | `None` (bypass) |
| `query` without `detail` | `("cc_get_leads", "search", {"mode": "query", "query", "start"})` |
| `phone` | `("cc_get_leads", "search", {"mode": "phone", "digits": <last 10 digits>})` |
| date range | `("cc_get_leads", "all" if can_view_all else user, {"mode": "range", "from_date", "to_date", "date_mode", "page_size", "start", "branch", "stage", "paginated"})` |

- [ ] **Step 1: Write the failing tests.**
  - `test_leads_detail_bypasses_cache`
  - `test_leads_search_and_phone_share_search_scope`
  - `test_leads_range_scope_all_for_managers_self_for_agents`
  - `test_leads_range_args_distinguish_pagination_and_filters`
  - `test_contact_manager_applied_after_cache`: patch `cached_read` to return
    `{"rows": [], "contact_manager": True}` for a non-contact-manager viewer. Assert
    `frappe.response["message"]["contact_manager"] is False`.

- [ ] **Step 2: Run the tests to see them fail.** Same module. Expected: an AttributeError
  for `_cache_plan`.

- [ ] **Step 3: Implement.**
  - Keep the role check, `can_view_all_leads` and `contact_manager` before the cache.
  - Move the three mode branches and the owner-name enrichment into a local `compute()`
    that returns the message dict. When `_cache_plan` returns `None`, call `compute()`
    directly.
  - After that, always set `message["contact_manager"]`, then run the existing detail-only
    blocks (`workflow_hint`, `enrich_lead_appointments`).

- [ ] **Step 4: Run the tests to see them pass.** Same module. Expected: `OK`.

- [ ] **Step 5: Commit**: `feat(cache): cache CC lead lists and searches by visibility scope`

### Task 5: Cache ConVox lead resolution for read paths

**Files:**
- Modify: `life_slimming/convox_lead_sync.py:12-62` (`resolve_lead`)
- Modify: `life_slimming/api/convox.py:334,357`
- Test: `life_slimming/tests/test_cache_endpoints.py`

**Interfaces:**
- Consumes: `cache.cached_read`.
- Produces: `resolve_lead(event, lookups=None, cache_reads: bool = False)`. When
  `cache_reads` is true, the owned and global SQL lookups go through
  `cached_read("convox_resolve", <agent user>, {"kind": "owned"|"global", "number": number}, fetch)`.

- [ ] **Step 1: Write the failing tests.** Patch `frappe.get_all` (agent users),
  `frappe.cache.get_value` (no mapped reference) and `frappe.db.sql`.
  - `test_resolve_lead_default_never_uses_cache`
  - `test_resolve_lead_cache_reads_keys_by_agent_kind_number`
  - `test_poll_and_history_pass_cache_reads_and_sync_event_does_not`: inspect the call
    sites with `unittest.mock.patch` on `resolve_lead`, or use source inspection of
    `convox.py` and `sync_event`.

- [ ] **Step 2: Run the tests to see them fail.** Same module. Expected: a TypeError
  (unexpected `cache_reads`).

- [ ] **Step 3: Implement.** Add the parameter and pass `cache_reads=True` at
  `convox.py:334` and `:357`. Update the "Never keep these results across requests"
  comment to say read paths may now reuse them for up to `ttl` seconds, and the write
  path never does.

- [ ] **Step 4: Run the tests to see them pass.** Expected: `OK`.

- [ ] **Step 5: Commit**: `feat(cache): reuse ConVox lead matches on read-only poll/history`

### Task 6: Move `life_cc_mobile_v18` into app code, with fallback

**Files:**
- Create: `life_slimming/api/server_scripts/life_cc_mobile_v18.py`
- Modify: `life_slimming/hooks.py`: replace the commented `override_whitelisted_methods`
  block at lines 414-417
- Modify: `life_slimming/api/CATALOG.md`: add a row with a note: "overrides the DB Server
  Script by name; falls back to it while `mobile_native` is 0"
- Modify: `life_slimming/api/catalog.json`:
  - set `"count": 152`
  - append an `endpoints` entry in the existing shape, with `id`/`source_name`/`legacy_method`
    `"life_cc_mobile_v18"`, `method` `"life_slimming.api.server_scripts.life_cc_mobile_v18.run"`,
    `source_modified` `"2026-11-05 16:01:10.326368"`, `source_sha256` from Step 1,
    `allow_guest`/`source_allow_guest` `false`, and `http_methods` `["POST"]`
  - with this entry, the existing `test_portal_api_migration` also checks that the new
    module is registered POST-only
- Test: `life_slimming/tests/test_mobile_v18.py`

**Interfaces:**
- Consumes: `cache.settings()`.
- Produces:
  - `run(**kwargs)`: `@script_endpoint(allow_guest=False)`. Returns
    `frappe.handler.run_server_script("life_cc_mobile_v18")` when
    `settings().mobile_native` is falsy, otherwise `_native()`.
  - `_native() -> None`: the script body; it sets `frappe.response["message"]`.
  - `ACTIONS`: the frozenset of the 21 action names.
  - `hooks.override_whitelisted_methods = {"life_cc_mobile_v18": "life_slimming.api.server_scripts.life_cc_mobile_v18.run"}`

- [ ] **Step 1: Export the source.** Run
  `cd /home/admin/frappe-bench && bench --site portal.lifescc.com mariadb -N -r -e "SELECT script FROM \`tabServer Script\` WHERE name='life_cc_mobile_v18'" > /tmp/claude-1001/-home-admin-frappe-bench/ad4f5428-742b-4817-870e-76674196bf7a/scratchpad/life_cc_mobile_v18.src.py`.
  This is read-only. Expected: 921 lines, starting `# LIFE_CC_SALES_OWNER_FIX_V1_20261105`.
  Record its SHA-256 in the module docstring.

- [ ] **Step 2: Write the failing tests.**
  - `test_actions_match_source`: the set of `action == "<x>"` literals in the module equals
    `ACTIONS` equals `{queue, dial, finish, sync, recording, calls, summary, appver, me, agents, number, wa_log, timing, live, team, plans, plan_save, plan_leads, targets, target_save, feed}`.
  - `test_falls_back_to_db_script_when_native_off`: patch `run_server_script` and assert
    it's called with `"life_cc_mobile_v18"`.
  - `test_native_when_switch_on`: patch `_native` and assert it's called.
  - `test_hooks_override_points_to_native_run`

- [ ] **Step 3: Run the tests to see them fail.** Run
  `… -m unittest life_slimming.tests.test_mobile_v18 -v`. Expected: an ImportError.

- [ ] **Step 4: Implement.** Put the exported body verbatim inside `_native()`, indented one
  level, following `api/MIGRATION.md` "Conversion details". Add `import json` at module
  top. Helper `def`s stay nested, because they close over `user`, `agent` and `is_mgr`.
  Make no logic changes.

- [ ] **Step 5: Run the tests to see them pass**, plus compile:
  `/home/admin/frappe-bench/env/bin/python -m py_compile life_slimming/api/server_scripts/life_cc_mobile_v18.py`.
  Expected: `OK`, and no output from `py_compile`.

- [ ] **Step 6: Commit**:
  `feat(mobile): native life_cc_mobile_v18 behind override, DB script fallback`

### Task 7: Cache the mobile read actions

**Files:**
- Modify: `life_slimming/api/server_scripts/life_cc_mobile_v18.py`
- Test: `life_slimming/tests/test_mobile_v18.py`

**Interfaces:**
- Consumes: `cache.cached_read` and `_native()` from Task 6.
- Produces:
  - `CACHED_ACTIONS = {"queue": (), "calls": ("date",), "summary": ("agent", "from", "to", "team"), "live": ("lead", "since"), "team": (), "feed": ("agent", "since", "team")}`
  - `_mobile_cache_key(action: str, agent: str, is_mgr: bool, fd: dict, today: str) -> tuple[str, str, dict] | None`:
    returns `None` for actions not in `CACHED_ACTIONS`, otherwise
    `(f"mobile_v18.{action}", f"{agent}|mgr={int(is_mgr)}", {"today": today, **{k: fd.get(k) for k in CACHED_ACTIONS[action]}})`.

- [ ] **Step 1: Write the failing tests.**
  - `test_write_actions_never_cached`: for each of
    `dial, finish, sync, recording, wa_log, timing, plan_save, target_save, number`,
    the key function returns `None`.
  - `test_read_action_key_scope_and_args`: `summary` with
    `fd={"from": "2026-11-01", "to": "2026-11-11", "team": "A", "x": 1}` gives args without
    `x` and scope `"a@x|mgr=1"`.
  - `test_cached_action_sets_response_from_cache`: patch `cached_read` to return
    `{"ok": 1}`. Run the dispatch wrapper for `queue` and assert
    `frappe.response["message"] == {"ok": 1}`.

- [ ] **Step 2: Run the tests to see them fail.** Same module. Expected: an AttributeError
  for `_mobile_cache_key`.

- [ ] **Step 3: Implement.**
  - Inside `_native()`, move the `if action == …` chain into a nested `_dispatch()`.
  - After `agent` and `is_mgr` are resolved: if `_mobile_cache_key(...)` returns a key,
    set `frappe.response["message"] = cache.cached_read(*key, compute)`, where `compute`
    calls `_dispatch()` and returns `frappe.response.get("message")`.
  - Otherwise call `_dispatch()`.

- [ ] **Step 4: Run the tests to see them pass**, plus Task 6's tests. Expected: `OK`.

- [ ] **Step 5: Commit**: `feat(cache): cache mobile agent read actions per agent scope`

### Task 8: `compare_mobile` rollout tool

**Files:**
- Create: `life_slimming/cache_tools.py`
- Test: `life_slimming/tests/test_mobile_v18.py`

**Interfaces:**
- Consumes: `life_cc_mobile_v18._native`, `CACHED_ACTIONS` and `frappe.handler.run_server_script`.
- Produces:
  `compare_mobile(agents: str | list[str], actions: str | list[str] | None = None) -> dict[str, dict[str, str]]`.
  - It accepts comma-separated strings, so it works with `bench execute --kwargs`.
  - `actions` defaults to every key of `CACHED_ACTIONS`.
  - For each agent and action it reports `"match"` or a short diff of the first 5
    differing paths.

- [ ] **Step 1: Write the failing tests.**
  - `test_refuses_non_read_actions`: `actions="dial"` raises `frappe.ValidationError`
    before anything runs.
  - `test_ignores_now_and_timestamp_fields`
  - `test_reports_mismatch_paths`: patch both implementations to set different
    `frappe.response["message"]` values.
  - `test_always_rolls_back_and_restores_user`: `frappe.db.rollback` is called, and
    `frappe.set_user` is reset to the original user, even when an implementation raises.

- [ ] **Step 2: Run the tests to see them fail.** Same module. Expected: an ImportError.

- [ ] **Step 3: Implement.** For each agent and action:
  1. Call `frappe.set_user(agent)` and set `frappe.local.form_dict = frappe._dict(action=a)`.
  2. Run the DB script and capture `frappe.response.get("message")`.
  3. Reset `frappe.response`, then run `_native()` with `cache.enabled` patched to return
    `False`, and capture again.
  4. Normalize by recursively dropping the keys `now` and `timestamp`, then compare.

  Use `try`/`finally` around everything for the rollback and user restore.

- [ ] **Step 4: Run the tests to see them pass.** Expected: `OK`.

- [ ] **Step 5: Commit**: `feat(cache): add read-only compare_mobile rollout check`

### Task 9: Whole-branch verification

**Files:** none new. If a check fails, fix it in the task that owns the code.

- [ ] **Step 1: Run the full test suite.** `life_slimming/tests/` has no `__init__.py`,
  so `discover` doesn't work; name the modules instead:
  `… -m unittest $(ls life_slimming/tests/test_*.py | sed 's#/#.#g; s#\.py$##')`.
  Expected: `OK`. The baseline on `main` was 44 tests, all passing, on 2026-11-11, and the
  total must now be 44 plus the new tests.
- [ ] **Step 2: Import check.**
  `/home/admin/frappe-bench/env/bin/python -c "import life_slimming.hooks as h, life_slimming.cache, life_slimming.cache_tools; print(h.before_request, h.override_whitelisted_methods)"`.
  Expected: three `before_request` entries and the override mapping.
- [ ] **Step 3: Check the default-off guarantee.** `git grep -n '"enabled": 0' life_slimming/cache.py`
  matches the defaults. No migration, patch or fixture writes site_config.
- [ ] **Step 4: Check that only the expected files changed.**
  `git diff --stat main...HEAD` shows only the files named in Tasks 1–8 plus the spec and
  this plan.
