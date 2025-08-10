
import frappe
from frappe.tests.utils import FrappeTestCase
from expense_pay.create_gl_entry import simulate_gl_entries, _ep_get_settings
from .utils import ensure_company, ensure_account, ensure_cost_center, ensure_vat_template

class TestExpensePayGL(FrappeTestCase):
    def setUp(self):
        self.company = ensure_company("TST Co")
        # Minimal masters
        self.bank = ensure_account("Bank - TST", self.company, account_type="Bank", is_group=0)
        self.exp_acc = ensure_account("Expense - TST", self.company, account_type="Expense Account", is_group=0)
        self.vat_acc = ensure_account("VAT - TST", self.company, account_type="Tax", is_group=0)
        self.cc_header = ensure_cost_center("HeadCC - TST", self.company, is_group=0)
        self.cc_row = ensure_cost_center("RowCC - TST", self.company, is_group=0)
        self.vat_tmpl = ensure_vat_template("VAT15 - TST", self.vat_acc, rate=15.0)

    def test_preview_balanced_single_tax(self):
        doc = {
            "company": self.company,
            "posting_date": "2025-01-01",
            "account_paid_from": self.bank,
            "default_cost_center": self.cc_header,
            "paid_amount": 115,
            "remarks": "Test",
            "expenses": [{
                "account_paid_to": self.exp_acc,
                "cost_center": self.cc_row,
                "amount_without_vat": 100,
                "vat_template": self.vat_tmpl,
                "vat_amount": 15,
                "project": None
            }]
        }
        res = simulate_gl_entries(doc)
        self.assertAlmostEqual(res["total_debit"], res["total_credit"])
        rows = res["rows"]
        # Credit bank uses header CC
        credit = [r for r in rows if r["credit"] > 0][0]
        self.assertEqual(credit["cost_center"], self.cc_header)
        # Expense + VAT use row CC
        debits = [r for r in rows if r["debit"] > 0]
        self.assertTrue(any(r["account"] == self.exp_acc and r["cost_center"] == self.cc_row for r in debits))
        self.assertTrue(any(r["account"] == self.vat_acc and r["cost_center"] == self.cc_row for r in debits))

    def test_multi_tax_split(self):
        # enable split
        s = _ep_get_settings()
        s.allow_multi_tax_per_row = 1
        # create two-tax template
        tmpl = ensure_vat_template("VAT5+10 - TST", self.vat_acc, rate=5.0)
        # add a second line (10% -> same VAT account for simplicity)
        vt = frappe.get_doc("Purchase Taxes and Charges Template", tmpl)
        vt.append("taxes", {
            "category": "Total",
            "charge_type": "On Net Total",
            "account_head": self.vat_acc,
            "rate": 10.0
        })
        vt.save()

        doc = {
            "company": self.company,
            "posting_date": "2025-01-01",
            "account_paid_from": self.bank,
            "default_cost_center": self.cc_header,
            "paid_amount": 115,
            "remarks": "Split",
            "expenses": [{
                "account_paid_to": self.exp_acc,
                "cost_center": self.cc_row,
                "amount_without_vat": 100,
                "vat_template": tmpl,
                "vat_amount": 15,
            }]
        }
        res = simulate_gl_entries(doc)
        debits = [r for r in res["rows"] if r["debit"] > 0 and r["account"] == self.vat_acc]
        # Should produce two VAT lines totaling 15
        self.assertTrue(len(debits) >= 2)
        self.assertAlmostEqual(sum(r["debit"] for r in debits), 15.0, places=2)

