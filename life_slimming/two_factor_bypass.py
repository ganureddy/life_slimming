"""Let selected users sign in without an OTP while 2FA stays on site-wide.

The exempt list lives in the "Two Factor Bypass Settings" single doctype
(child table "Two Factor Bypass User").

frappe.twofactor.two_factor_is_enabled_for_() is the one chokepoint every 2FA
decision passes through:

    auth.LoginManager.login()  -> should_run_2fa() -> two_factor_is_enabled()
    ldap_settings login        -> should_run_2fa() -> two_factor_is_enabled()
    twofactor.confirm_otp_token()                  -> two_factor_is_enabled_for_()

should_run_2fa() and two_factor_is_enabled() resolve the name from twofactor's
module globals at call time, so wrapping that single function covers every
login path. install() is wired to the `before_request` hook so the wrapper is
in place on every worker before any request is dispatched.

Nothing in frappe core is modified.
"""

import functools

import frappe

SETTINGS_DOCTYPE = "Two Factor Bypass Settings"
CHILD_DOCTYPE = "Two Factor Bypass User"
CHILD_FIELDNAME = "users"
CACHE_KEY = "two_factor_bypass_users"
CACHE_TTL = 3600  # safety net; saving the settings doc busts the cache immediately


def get_bypassed_users() -> set:
	"""Emails of users allowed to skip the OTP step. Cached in redis."""
	cached = frappe.cache.get_value(CACHE_KEY)
	if cached is None:
		cached = _fetch_bypassed_users()
		frappe.cache.set_value(CACHE_KEY, cached, expires_in_sec=CACHE_TTL)

	return set(cached)


def _fetch_bypassed_users() -> list:
	try:
		# The doctype may not be migrated yet -- never break login over that.
		if not frappe.db.table_exists(CHILD_DOCTYPE):
			return []

		if not frappe.db.get_single_value(SETTINGS_DOCTYPE, "enabled"):
			return []

		child = frappe.qb.DocType(CHILD_DOCTYPE)
		return (
			frappe.qb.from_(child)
			.select(child.user)
			.distinct()
			.where(child.parent == SETTINGS_DOCTYPE)
			.where(child.parenttype == SETTINGS_DOCTYPE)
			.where(child.parentfield == CHILD_FIELDNAME)
			.where(child.enabled == 1)
			.where(child.user.isnotnull())
			.where(child.user != "")
		).run(pluck=True)
	except Exception:
		# Fail closed: on any error keep asking for the OTP.
		frappe.log_error(title="2FA bypass lookup failed")
		return []


def is_bypassed(user) -> bool:
	"""True if `user` (email string or User doc) may skip 2FA."""
	name = user if isinstance(user, str) else getattr(user, "name", None)
	if not name or name == "Guest":
		return False

	return name in get_bypassed_users()


def clear_bypass_cache(doc=None, method=None):
	"""Also usable as a doc_events handler (hence the unused args)."""
	frappe.cache.delete_value(CACHE_KEY)


_patched = False


def install():
	"""`before_request` hook: wrap frappe.twofactor.two_factor_is_enabled_for_."""
	global _patched

	if _patched:
		return

	import frappe.twofactor as twofactor

	original = twofactor.two_factor_is_enabled_for_
	if getattr(original, "_bypass_wrapped", False):
		_patched = True
		return

	@functools.wraps(original)
	def two_factor_is_enabled_for_(user):
		if is_bypassed(user):
			return False

		return original(user)

	two_factor_is_enabled_for_._bypass_wrapped = True
	twofactor.two_factor_is_enabled_for_ = two_factor_is_enabled_for_
	_patched = True
