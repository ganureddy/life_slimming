"""Read-only Price-List data assembled with Frappe permissions."""

import frappe


@frappe.whitelist(methods=["POST"])
def active_offers():
    if frappe.session.user == "Guest":
        raise frappe.PermissionError

    today = frappe.utils.nowdate()
    rules = frappe.get_list(
        "Pricing Rule",
        filters={"disable": 0, "selling": 1, "apply_on": "Item Code"},
        fields=[
            "name", "priority", "apply_on", "price_or_product_discount",
            "rate", "discount_percentage", "discount_amount", "min_qty",
            "max_qty", "valid_from", "valid_upto",
        ],
        limit_page_length=10001,
    )
    if len(rules) > 10000:
        frappe.throw("Too many pricing rules to show safely.")
    active = [
        row for row in rules
        if (not row.valid_from or str(row.valid_from)[:10] <= today)
        and (not row.valid_upto or str(row.valid_upto)[:10] >= today)
    ]
    if not active:
        return {"offers": []}

    items = frappe.get_all(
        "Pricing Rule Item Code",
        filters={"parent": ["in", [row.name for row in active]]},
        fields=["parent", "item_code"],
        limit_page_length=0,
    )
    by_rule = {row.name: row for row in active}
    return {
        "offers": [
            {**by_rule[item.parent], "item_code": item.item_code}
            for item in items if item.item_code and item.parent in by_rule
        ]
    }


def audit_offer_shape():
    """Read-only Bench check; return counts without business prices or names."""
    offers = active_offers()["offers"]
    return {
        "mapped_offers": len(offers),
        "distinct_items": len({offer["item_code"] for offer in offers}),
    }
