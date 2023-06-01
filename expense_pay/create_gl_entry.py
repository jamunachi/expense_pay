import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

def create_gl_entries(doc, method):
    gl_entries = []
    
    # Create GL entry for Account Paid From
    gl_entry = {
        "doctype": "GL Entry",
        "posting_date": doc.posting_date,
        "account": doc.account_paid_from,
        "cost_center": doc.default_cost_center,
        "debit": 0,
        "credit": doc.paid_amount,
        "debit_in_account_currency": 0,
        "credit_in_account_currency": doc.paid_amount,
        "against": ", ".join([d.account_paid_to for d in doc.expenses]),
        "voucher_type": _("Expenses Entry"),
        "voucher_no": doc.name,
        "is_opening": "No",
        "is_advance": "No",
        "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
        "company": doc.company
    }
    gl_entries.append(gl_entry)

    # Create GL entries for Expenses child table
    for expense in doc.expenses:
        gl_entry = {
            "doctype": "GL Entry",
            "posting_date": doc.posting_date,
            "account": expense.account_paid_to,
            "cost_center": expense.cost_center,
            "debit": expense.amount,
            "credit": 0,
            "debit_in_account_currency": expense.amount,
            "credit_in_account_currency": 0,
            "against": doc.account_paid_from,
            "voucher_type": _("Expenses Entry"),
            "voucher_no": doc.name,
            "is_opening": "No",
            "is_advance": "No",
            "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
            "company": doc.company
        }
        gl_entries.append(gl_entry)

    for gl_entry in gl_entries:
        gle = frappe.new_doc("GL Entry")
        gle.update(gl_entry)
        gle.flags.ignore_permissions = 1
        gle.flags.notify_update = False
        gle.submit()
