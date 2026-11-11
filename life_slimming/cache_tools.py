"""Rollout checks for the read cache. Run from the bench, never over HTTP.

    bench --site portal.lifescc.com execute life_slimming.cache_tools.compare_mobile \\
        --kwargs "{'agents': 'agent1@lifescc.com,agent2@lifescc.com'}"

compare_mobile runs each read-only life_cc_mobile_v18 action twice for every
agent, once through the DB Server Script and once through the native copy (with
the read cache off), and reports "match" or where the results differ. It
switches users with frappe.set_user, so it must never be whitelisted.
"""
import json

import frappe
from frappe.handler import run_server_script

from life_slimming import cache as read_cache
from life_slimming.api.server_scripts import life_cc_mobile_v18 as mobile

IGNORED_KEYS = frozenset({"now", "timestamp"})
MAX_PATHS = 5


def _as_list(value):
	if value is None:
		return []
	if isinstance(value, str):
		return [item.strip() for item in value.split(",") if item.strip()]
	return [str(item).strip() for item in value if str(item).strip()]


def _normalize(value):
	"""JSON-shaped copy without per-call clock fields."""
	value = json.loads(json.dumps(value, default=str))

	def strip(item):
		if isinstance(item, dict):
			return {key: strip(val) for key, val in item.items() if key not in IGNORED_KEYS}
		if isinstance(item, list):
			return [strip(val) for val in item]
		return item

	return strip(value)


def _differences(left, right, path="", found=None):
	found = [] if found is None else found
	if len(found) >= MAX_PATHS:
		return found
	if isinstance(left, dict) and isinstance(right, dict):
		for key in sorted(set(left) | set(right), key=str):
			child = f"{path}.{key}" if path else str(key)
			if key not in left or key not in right:
				found.append(child)
			else:
				_differences(left[key], right[key], child, found)
			if len(found) >= MAX_PATHS:
				break
	elif isinstance(left, list) and isinstance(right, list):
		for index in range(max(len(left), len(right))):
			child = f"{path}[{index}]"
			if index >= len(left) or index >= len(right):
				found.append(child)
			else:
				_differences(left[index], right[index], child, found)
			if len(found) >= MAX_PATHS:
				break
	elif left != right:
		found.append(path or "(whole result)")
	return found


def _capture(action, run):
	frappe.local.form_dict = frappe._dict(action=action)
	frappe.local.response = frappe._dict(docs=[])
	run()
	return frappe.response.get("message")


def _run_native(action):
	"""Native copy with the read cache switched off for this request only."""
	original_conf = frappe.local.conf
	frappe.local.conf = frappe._dict(original_conf)
	frappe.local.conf[read_cache.CONFIG_KEY] = {**read_cache.settings(), "enabled": 0}
	try:
		return _capture(action, mobile._native)
	finally:
		frappe.local.conf = original_conf


def compare_mobile(agents, actions=None) -> dict:
	"""{agent: {action: "match" | "differs at …" | "error in db|native: …"}} for read actions only."""
	agents = _as_list(agents)
	actions = _as_list(actions) or list(mobile.CACHED_ACTIONS)
	refused = [action for action in actions if action not in mobile.CACHED_ACTIONS]
	if refused:
		raise frappe.ValidationError(f"compare_mobile only runs read-only actions; refused: {', '.join(refused)}")

	original_user = frappe.session.user
	original_form = frappe.local.form_dict
	original_response = frappe.local.response
	report = {}
	try:
		for agent in agents:
			frappe.set_user(agent)
			report[agent] = {}
			for action in actions:
				try:
					stage = "db"
					from_db = _capture(action, lambda: run_server_script("life_cc_mobile_v18"))
					stage = "native"
					from_native = _run_native(action)
				except Exception as error:
					report[agent][action] = f"error in {stage}: {type(error).__name__}: {error}"
					continue
				finally:
					frappe.db.rollback()
				differences = _differences(_normalize(from_db), _normalize(from_native))
				report[agent][action] = "match" if not differences else "differs at " + "; ".join(differences)
	finally:
		frappe.db.rollback()
		frappe.set_user(original_user)
		frappe.local.form_dict = original_form
		frappe.local.response = original_response
	return report
