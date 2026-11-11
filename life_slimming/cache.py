"""Shared Redis read cache for busy life_slimming read endpoints.

Freshness rule: a user always sees their own committed writes on the next read,
and other people's writes within ``ttl`` seconds (default 30).

* ``cached_read`` keeps one entry per (namespace, scope, args). Each entry records
  the time its computation *started*; it is reused only while Redis keeps it
  (``ttl``) and while it is newer than the viewer's last committed write.
* Write stamps are set after every committed transaction that wrote anything
  (see ``arm_write_tracking``), so writes through ``frappe.db.set_value``,
  ``db_set`` or raw SQL count too.

Everything is off until ``life_slimming_cache.enabled`` is set in site_config.
Permission checks never go through this module: callers run them first and
pass only their data-fetching part as ``compute``.
"""
import hashlib
import json
import pickle
import time
import zlib
from collections.abc import Callable
from typing import Any

import frappe

CONFIG_KEY = "life_slimming_cache"
DEFAULTS = {"enabled": 0, "ttl": 30, "max_entry_bytes": 1048576, "disabled": [], "mobile_native": 0}

ENTRY_PREFIX = "life_slimming:rc:"
STAMP_PREFIX = "life_slimming:lw:"
STATS_PREFIX = "life_slimming:rc:stats:"
REDIS_FIELDS = ("used_memory", "evicted_keys", "keyspace_hits", "keyspace_misses")

# MariaDB runs REPEATABLE READ: a request reads from the snapshot taken at its
# transaction's first SELECT, which can come before arm_write_tracking (session
# loading). Entries are therefore stamped with the transaction start minus this
# margin, never with the moment compute() runs.
SNAPSHOT_MARGIN_SECONDS = 1.0
TXN_STARTED_ATTR = "life_slimming_txn_started"

_error_logged = False


def _now() -> float:
	return time.time()


def _positive_int(value, default):
	try:
		number = int(value)
	except (TypeError, ValueError, OverflowError):
		return default
	return number if number > 0 else default


def settings() -> frappe._dict:
	"""Defaults merged with ``life_slimming_cache`` (a dict or a JSON string)."""
	raw = (frappe.conf or {}).get(CONFIG_KEY)
	if isinstance(raw, str):
		try:
			raw = json.loads(raw)
		except ValueError:
			raw = None
	if not isinstance(raw, dict):
		raw = {}
	disabled = raw.get("disabled")
	if isinstance(disabled, str):
		disabled = [disabled]
	return frappe._dict(
		enabled=1 if _positive_int(raw.get("enabled"), 0) else 0,
		ttl=_positive_int(raw.get("ttl"), DEFAULTS["ttl"]),
		max_entry_bytes=_positive_int(raw.get("max_entry_bytes"), DEFAULTS["max_entry_bytes"]),
		disabled=[str(item) for item in disabled] if isinstance(disabled, list | tuple) else [],
		mobile_native=1 if _positive_int(raw.get("mobile_native"), 0) else 0,
	)


def enabled(namespace: str) -> bool:
	"""Master switch on and neither ``namespace`` nor a dotted prefix disabled."""
	config = settings()
	if not config.enabled:
		return False
	return not any(namespace == item or namespace.startswith(item + ".") for item in config.disabled)


def _session_user() -> str | None:
	try:
		return frappe.session.user
	except Exception:
		return None


def _args_hash(args: dict) -> str:
	encoded = json.dumps(args, sort_keys=True, default=str).encode()
	return hashlib.sha1(encoded).hexdigest()[:16]


def _entry_key(namespace: str, scope: str, args: dict) -> str:
	return f"{ENTRY_PREFIX}{namespace}:{scope}:{_args_hash(args)}"


def _stamp_key(user: str) -> str:
	return f"{STAMP_PREFIX}{user}"


def _count(namespace: str, field: str, amount: int = 1) -> None:
	try:
		frappe.cache.hincrby(frappe.cache.make_key(STATS_PREFIX + namespace), field, int(amount))
	except Exception:
		pass


def _report_error(namespace: str) -> None:
	global _error_logged
	_count(namespace, "error")
	if _error_logged:
		return
	_error_logged = True
	try:
		frappe.log_error(title="life_slimming read cache error")
	except Exception:
		pass


def stamp(user: str) -> float:
	"""Epoch of ``user``'s last committed write, or 0.0."""
	value = frappe.cache.get_value(_stamp_key(user), expires=True)
	try:
		return float(value) if value else 0.0
	except (TypeError, ValueError):
		return 0.0


def cached_read(namespace: str, scope: str, args: dict, compute: Callable[[], Any]) -> Any:
	"""Return ``compute()``'s result, reusing a fresh-enough shared entry."""
	if not enabled(namespace):
		return compute()
	user = _session_user()
	if not user or user == "Guest":
		return compute()
	config = settings()
	key = _entry_key(namespace, scope, args)
	try:
		entry = frappe.cache.get_value(key, expires=True)
		if entry is not None:
			if entry.get("too_large"):
				# Recently too big to store: skip pickling it again until the marker expires.
				_count(namespace, "too_large")
				return compute()
			if entry["t"] > stamp(user):
				value = pickle.loads(zlib.decompress(entry["z"]))
				_count(namespace, "hit")
				return value
			_count(namespace, "stale_own_write")
		else:
			_count(namespace, "miss")
	except Exception:
		_report_error(namespace)
		return compute()

	view_started = getattr(frappe.local, TXN_STARTED_ATTR, None)
	if view_started is None:
		# Not armed (e.g. a background job): the snapshot age is unknown, so don't share it.
		_count(namespace, "unarmed")
		return compute()
	started_at = min(view_started, _now()) - SNAPSHOT_MARGIN_SECONDS
	timer = time.perf_counter()
	result = compute()
	_count(namespace, "compute_ms", round((time.perf_counter() - timer) * 1000))
	try:
		blob = zlib.compress(pickle.dumps(result))
		if len(blob) > config.max_entry_bytes:
			_count(namespace, "too_large")
			frappe.cache.set_value(key, {"t": started_at, "too_large": True}, expires_in_sec=config.ttl)
		else:
			frappe.cache.set_value(key, {"t": started_at, "z": blob}, expires_in_sec=config.ttl)
			_count(namespace, "stored_bytes", len(blob))
	except Exception:
		_report_error(namespace)
	return result


def mark_write(user: str | None = None) -> None:
	"""Record that ``user`` (default: the session user) has just committed a write."""
	config = settings()
	user = user or _session_user()
	if not config.enabled or not user or user == "Guest":
		return
	try:
		frappe.cache.set_value(_stamp_key(user), _now(), expires_in_sec=max(120, 2 * config.ttl))
	except Exception:
		_report_error("write_tracking")


def arm_write_tracking() -> None:
	"""``before_request`` hook: stamp the request's user after each commit that wrote.

	CallbackManager.run() drains its queue until it is empty, so a callback must
	never add to the queue that is currently running. The chain below only ever adds
	to the *other* queues, and re-arms itself after every commit and rollback
	(commit() resets the rollback queues; rollback() resets the commit queues).

	before_request runs before validate_auth, so API-key/token requests are still
	Guest here: arm for every request and resolve the user at commit time. This hook
	runs on every request and must never raise.
	"""
	try:
		if not settings().enabled or frappe.db is None:
			return
		_arm()
	except Exception:
		_report_error("write_tracking")


def _arm() -> None:
	# A new transaction (and read view) starts now: at request start, or right
	# after COMMIT / ROLLBACK, which both begin() the next transaction.
	setattr(frappe.local, TXN_STARTED_ATTR, _now())
	frappe.db.before_commit.add(_before_commit)
	frappe.db.before_rollback.add(_before_rollback)


def _before_commit() -> None:
	# transaction_writes is still counted here; the COMMIT statement resets it.
	user = _session_user()
	wrote = frappe.db.transaction_writes > 0
	frappe.db.after_commit.add(lambda: _after_commit(user, wrote))


def _after_commit(user: str | None, wrote: bool) -> None:
	# After COMMIT: any read that starts from now on sees this write.
	if wrote and user and user != "Guest":
		mark_write(user)
	_arm()


def _before_rollback() -> None:
	frappe.db.after_rollback.add(_arm)


@frappe.whitelist()
def stats() -> dict:
	"""Per-namespace counters and Redis memory figures (System Manager only)."""
	frappe.only_for("System Manager")
	namespaces = {}
	for full_key in frappe.cache.get_keys(STATS_PREFIX):
		name = full_key.decode() if isinstance(full_key, bytes) else str(full_key)
		namespace = name.split(STATS_PREFIX, 1)[1]
		# RedisWrapper.hgetall unpickles values; HINCRBY counters are raw integers.
		raw = frappe.cache.execute_command("HGETALL", full_key) or {}
		namespaces[namespace] = {
			(field.decode() if isinstance(field, bytes) else field): int(value) for field, value in raw.items()
		}
	info = frappe.cache.info()
	return {"namespaces": namespaces, "redis": {field: info.get(field) for field in REDIS_FIELDS}}
