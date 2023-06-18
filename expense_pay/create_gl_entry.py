import frappe
from frappe import _
from frappe.utils import  now

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
        "cost_center": doc.default_cost_center,
        "voucher_no": doc.name,
        "is_opening": "No",
        "is_advance": "No",
        "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
        "company": doc.company,
        "remarks": doc.remarks
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
            "cost_center": expense.cost_center, # Added this line
            "voucher_type": _("Expenses Entry"),
            "voucher_no": doc.name,
            "is_opening": "No",
            "is_advance": "No",
            "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
            "company": doc.company,
            "remarks": expense.remarks
        }
        gl_entries.append(gl_entry)

    for gl_entry in gl_entries:
        gle = frappe.new_doc("GL Entry")
        gle.update(gl_entry)
        gle.flags.ignore_permissions = 1
        gle.flags.notify_update = False
        gle.submit()


def cancel_gl_entries(doc, method):

    # Ignore linked doctypes
    doc.ignore_linked_doctypes = ("GL Entry",)    
    
    
    gl_entries = []
    
    # Create GL entry for Account Paid From
    gl_entry = {
        "doctype": "GL Entry",
        "posting_date": doc.posting_date,
        "account": doc.account_paid_from,
        "cost_center": doc.default_cost_center,
        "debit": doc.paid_amount,
        "credit": 0,
        "debit_in_account_currency": doc.paid_amount,
        "cost_center": doc.default_cost_center,
        "credit_in_account_currency": 0,
        "against": ", ".join([d.account_paid_to for d in doc.expenses]),
        "voucher_type": _("Expenses Entry"),
        "voucher_no": doc.name,
        "is_opening": "No",
        "is_advance": "No",
        "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
        "company": doc.company,
        "is_cancelled": 1,
        "to_rename": 1,
        "remarks": "On Cancelled " + doc.remarks
    }
    gl_entries.append(gl_entry)

    # Create GL entries for Expenses child table
    for expense in doc.expenses:
        gl_entry = {
            "doctype": "GL Entry",
            "posting_date": doc.posting_date,
            "account": expense.account_paid_to,
            "cost_center": expense.cost_center,
            "debit": 0,
            "credit": expense.amount,
            "cost_center": expense.cost_center, # Added this line
            "debit_in_account_currency": 0,
            "credit_in_account_currency": expense.amount,
            "against": doc.account_paid_from,
            "voucher_type": _("Expenses Entry"),
            "voucher_no": doc.name,
            "is_opening": "No",
            "is_advance": "No",
            "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
            "company": doc.company,
            "is_cancelled": 1,
            "to_rename": 1,
            "remarks": "On Cancelled " + expense.remarks
        }
        gl_entries.append(gl_entry)

    for gl_entry in gl_entries:
        gle = frappe.new_doc("GL Entry")
        gle.update(gl_entry)
        gle.flags.ignore_permissions = 1
        gle.flags.notify_update = False
        gle.submit()
        voucher_type = gle.voucher_type
        voucher_no = gle.voucher_no
        def set_as_cancel(voucher_type, voucher_no):
            """
            Set is_cancelled=1 in all original gl entries for the voucher
            """
            frappe.db.sql(
                """UPDATE `tabGL Entry` SET is_cancelled = 1,
                modified=%s, modified_by=%s
                where voucher_type=%s and voucher_no=%s and is_cancelled = 0""",
                (now(), frappe.session.user, voucher_type, voucher_no),
            )
        set_as_cancel(voucher_type, voucher_no)
