# Copyright (c) 2025, Kishan Panchal and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ExpenseEntrySettings(Document):
    pass


@frappe.whitelist()
def get_ui_filters():
    s = frappe.get_single("Expense Entry Settings")

    def to_list(val):
        if not val:
            return []
        out = []
        for line in val.splitlines():
            for p in line.split(","):
                p = p.strip()
                if p:
                    out.append(p)
        return out

    return {
        "only_leaf_accounts": int(getattr(s, "only_leaf_accounts", 0) or 0),
        "only_leaf_cost_centers": int(getattr(s, "only_leaf_cost_centers", 0) or 0),
        "debit_account_types": to_list(getattr(s, "debit_account_types", "")),
        "credit_account_types": to_list(getattr(s, "credit_account_types", "")),
        "enable_import_ui": int(getattr(s, "enable_import_ui", 0) or 0),
    }
