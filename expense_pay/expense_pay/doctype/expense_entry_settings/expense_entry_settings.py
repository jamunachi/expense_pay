# Copyright (c) 2025, Kishan Panchal and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ExpenseEntrySettings(Document):
	pass
<<<<<<< HEAD
=======


import frappe

@frappe.whitelist()
def get_ui_filters():
    s = frappe.get_single("Expense Entry Settings")
    def to_list(val):
        if not val: return []
        out = []
        for line in val.splitlines():
            for p in line.split(','):
                p = p.strip()
                if p: out.append(p)
        return out
    return {
        "only_leaf_accounts": int(s.only_leaf_accounts or 0),
        "only_leaf_cost_centers": int(s.only_leaf_cost_centers or 0),
        "debit_account_types": to_list(s.debit_account_types),
        "credit_account_types": to_list(s.credit_account_types),
    ,
        "enable_import_ui": int(s.enable_import_ui or 0)
    }

>>>>>>> origin/release/v1.0.0
