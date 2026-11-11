"""Test doubles for frappe.cache (RedisWrapper) used by the read-cache tests.

FakeCache mirrors the RedisWrapper behaviour the cache module depends on
(frappe/utils/redis_wrapper.py in Frappe 15.109): keys get the site prefix in
make_key, values are pickled, get_value keeps a request-local copy unless
expires=True, and hgetall unpickles field values. Raw counters written with
HINCRBY therefore cannot be read back with hgetall, just like in production.
"""
import pickle

import redis


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
