"""Test doubles for frappe.cache (RedisWrapper) used by the read-cache tests.

FakeCache mirrors the RedisWrapper behaviour the cache module depends on
(frappe/utils/redis_wrapper.py in Frappe 15.109): keys get the site prefix in
make_key, values are pickled, get_value keeps a request-local copy unless
expires=True, and hgetall unpickles field values. Raw counters written with
HINCRBY therefore cannot be read back with hgetall, just like in production.
"""
import pickle

import redis
from frappe.utils import CallbackManager


class GuardedCallbackManager(CallbackManager):
	"""CallbackManager that fails loudly when a callback re-adds to the queue being run.

	CallbackManager.run() drains its deque until empty, so adding to the queue that
	is currently running would loop forever in production.
	"""

	def __init__(self, name):
		super().__init__()
		self.name = name
		self.running = False

	def add(self, func):
		if self.running:
			raise AssertionError(f"callback added to {self.name} while it was running")
		super().add(func)

	def run(self):
		self.running = True
		try:
			super().run()
		finally:
			self.running = False

	def __len__(self):
		return len(self._functions)


class FakeDB:
	"""Mirrors Database.commit()/rollback() in frappe/database/database.py:1173-1201.

	transaction_writes is reset by the COMMIT/ROLLBACK statement itself, i.e. after
	before_commit / before_rollback have run. ``clock`` advances by one second at the
	COMMIT statement so tests can tell before-commit time from after-commit time.
	"""

	def __init__(self, clock=None):
		self.clock = clock
		self.transaction_writes = 0
		self.before_commit = GuardedCallbackManager("before_commit")
		self.after_commit = GuardedCallbackManager("after_commit")
		self.before_rollback = GuardedCallbackManager("before_rollback")
		self.after_rollback = GuardedCallbackManager("after_rollback")

	def write(self, count=1):
		self.transaction_writes += count

	def commit(self):
		self.before_rollback.reset()
		self.after_rollback.reset()
		self.before_commit.run()
		self.transaction_writes = 0  # "commit" statement
		if self.clock is not None:
			self.clock.advance(1)
		self.after_commit.run()

	def rollback(self):
		self.before_commit.reset()
		self.after_commit.reset()
		self.before_rollback.run()
		self.transaction_writes = 0  # "rollback" statement
		self.after_rollback.run()


class FakeClock:
	def __init__(self, now=1_000_000.0):
		self.now = float(now)

	def __call__(self):
		return self.now

	def advance(self, seconds):
		self.now += seconds


class FakeCache:
	db_name = "testdb"

	def __init__(self, clock):
		self.clock = clock
		self.store = {}  # full key (bytes) -> (pickled bytes, expires_at or None)
		self.hashes = {}  # full key (bytes) -> {field bytes: value bytes}
		self.local = {}  # request-local copies, like frappe.local.cache
		self.fail = False

	def _check(self):
		if self.fail:
			raise redis.exceptions.TimeoutError("fake redis is down")

	def _alive(self, key):
		item = self.store.get(key)
		if item is None:
			return None
		value, expires_at = item
		if expires_at is not None and self.clock() >= expires_at:
			del self.store[key]
			return None
		return value

	def make_key(self, key, user=None, shared=False):
		if shared:
			return key
		if user:
			key = f"user:{user}:{key}"
		return f"{self.db_name}|{key}".encode()

	def set_value(self, key, val, user=None, expires_in_sec=None, shared=False):
		self._check()
		full = self.make_key(key, user, shared)
		if not expires_in_sec:
			self.local[full] = val
		expires_at = self.clock() + expires_in_sec if expires_in_sec else None
		self.store[full] = (pickle.dumps(val), expires_at)

	def get_value(self, key, generator=None, user=None, expires=False, shared=False):
		self._check()
		full = self.make_key(key, user, shared)
		if full in self.local:
			return self.local[full]
		raw = self._alive(full)
		val = pickle.loads(raw) if raw is not None else None
		if not expires:
			self.local[full] = val
		return val

	def delete_value(self, keys, user=None, make_keys=True, shared=False):
		self._check()
		if not isinstance(keys, list | tuple):
			keys = (keys,)
		for key in keys:
			full = self.make_key(key, user, shared) if make_keys else key
			self.local.pop(full, None)
			self.store.pop(full, None)
			self.hashes.pop(full, None)

	def hincrby(self, name, field, amount=1):
		self._check()
		fields = self.hashes.setdefault(name, {})
		field = field.encode() if isinstance(field, str) else field
		fields[field] = str(int(fields.get(field, b"0")) + int(amount)).encode()
		return int(fields[field])

	def hgetall(self, name):
		# RedisWrapper.hgetall prefixes the name and unpickles every value.
		self._check()
		return {k: pickle.loads(v) for k, v in self.hashes.get(self.make_key(name), {}).items()}

	def execute_command(self, command, *args):
		self._check()
		if command.upper() == "HGETALL":
			return dict(self.hashes.get(args[0], {}))
		raise NotImplementedError(command)

	def get_keys(self, key):
		self._check()
		prefix = self.make_key(key)
		live = [k for k in list(self.store) if self._alive(k) is not None]
		return [k for k in live + list(self.hashes) if k.startswith(prefix)]

	def info(self, *args):
		self._check()
		return {"used_memory": 1234, "evicted_keys": 0, "keyspace_hits": 10, "keyspace_misses": 2}

	def new_request(self):
		"""Forget request-local copies, as Frappe does at the start of a request."""
		self.local.clear()
