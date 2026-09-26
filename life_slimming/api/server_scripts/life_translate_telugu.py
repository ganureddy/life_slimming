"""Followup master diet english to telugu transfer

Original API: life_translate_telugu
Source modified: 2026-08-19 11:41:44.950734
See ../CATALOG.md for migration notes and validation limits.
"""

import json
import re

import frappe
from frappe.integrations.utils import make_post_request as _make_post_request
from frappe.utils.safe_exec import read_sql as _read_sql
from frappe.utils.safe_exec import call_whitelisted_function as _call_whitelisted
from life_slimming.api._runtime import script_endpoint


@script_endpoint(allow_guest=False)
def run(**kwargs):
    # ============================================================
    # ERPNext Server Script
    # Script Type : API
    # API Method  : life_translate_telugu
    # Allow Guest : NO
    # ============================================================
    #
    # IMPORTANT:
    # This version NEVER throws an error just because the Google API key is
    # missing. The Followup Master will fall back to its built-in common
    # diet-note Telugu translations without producing HTTP 417 errors.
    #
    # For arbitrary English -> Telugu translation, replace the placeholder
    # below with a valid Google Cloud Translation API key.
    # ============================================================

    GOOGLE_TRANSLATE_API_KEY = frappe.conf.get("life_google_translate_api_key") or "PASTE_API_KEY_IN_SITE_CONFIG"

    text = (frappe.form_dict.get("text") or "").strip()

    if not text:
        frappe.response["message"] = {
            "translated": "",
            "configured": 0 if GOOGLE_TRANSLATE_API_KEY.startswith("PASTE_") else 1
        }

    elif GOOGLE_TRANSLATE_API_KEY.startswith("PASTE_"):
        # Do not throw. Let the web page use its local translation dictionary.
        frappe.response["message"] = {
            "translated": "",
            "configured": 0
        }

    elif len(text) > 500:
        frappe.response["message"] = {
            "translated": "",
            "configured": 1,
            "error": "Maximum translation length is 500 characters."
        }

    else:
        url = (
            "https://translation.googleapis.com/language/translate/v2"
            "?key=" + GOOGLE_TRANSLATE_API_KEY
        )

        payload = json.dumps({
            "q": text,
            "source": "en",
            "target": "te",
            "format": "text"
        })

        translated = ""
        error = ""

        try:
            result = _make_post_request(
                url,
                headers={"Content-Type": "application/json; charset=utf-8"},
                data=payload
            )

            if result and result.get("data"):
                translations = result.get("data", {}).get("translations") or []
                if translations:
                    translated = translations[0].get("translatedText") or ""

        except Exception as e:
            # Do not raise a Frappe exception because that becomes HTTP 417 and
            # causes repeated browser console errors while the user is typing.
            error = str(e)

        frappe.response["message"] = {
            "translated": translated,
            "configured": 1,
            "error": error
        }
