<<<<<<< HEAD
# Copyright (c) 2023, Kishan Panchal and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase


class TestExpensesEntry(FrappeTestCase):
	pass
=======

import frappe
from frappe.tests.utils import FrappeTestCase

class TestExpensesEntry(FrappeTestCase):
    def test_preview_balances(self):
        from expense_pay.create_gl_entry import simulate_gl_entries
        doc = {
            "company": "Test",
            "posting_date": "2025-01-01",
            "account_paid_from": "Bank - T",
            "default_cost_center": "Main - T",
            "paid_amount": 115,
            "remarks": "Test",
            "expenses": [{
                "account_paid_to": "Expenses - T",
                "cost_center": "Dept - T",
                "amount_without_vat": 100,
                "vat_template": None,
                "vat_amount": 15,
                "project": None
            }]
        }
        res = simulate_gl_entries(doc)
        self.assertAlmostEqual(res["total_debit"], res["total_credit"])
>>>>>>> origin/release/v1.0.0
