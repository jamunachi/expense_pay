import frappe
from frappe import _
from frappe.utils import  now, logger
from erpnext.accounts.utils import _delete_gl_entries

logger.set_log_level("DEBUG")
logger = frappe.logger("expensepay", file_count=1, allow_site=True)

def create_gl_entries(doc, method):
    gl_entries = []
    
    # Create GL entry for Account Paid From
    paid_to_accounts = ", ".join([d.account_paid_to for d in doc.expenses])
    
    # Update the remarks with VAT details
    vat_remarks = ""
    for expense in doc.expenses:
        vat_remarks += f"Expense: {expense.account_paid_to}, VAT: {expense.vat_amount} ({expense.vat_template})\n"

    main_remarks = f"{doc.remarks}\nVAT Info:\n{vat_remarks}"  # Append VAT Info to main remarks
    
    # GL entry for the account paid from
    gl_entry = {
        "doctype": "GL Entry",
        "posting_date": doc.posting_date,
        "account": doc.account_paid_from,
        "cost_center": (doc.default_cost_center if doc.default_cost_center else ""),
        "debit": 0,
        "credit": doc.paid_amount,
        "debit_in_account_currency": 0,
        "credit_in_account_currency": doc.paid_amount,
        "against": paid_to_accounts,
        "voucher_type": _("Expenses Entry"),
        "voucher_no": doc.name,
        "is_opening": "No",
        "is_advance": "No",
        "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
        "company": doc.company,
        "remarks": main_remarks  # Use updated remarks with VAT info
    }
    gl_entries.append(gl_entry)

    # Create GL entries for each expense and VAT
    for expense in doc.expenses:
        # Update the remarks to include VAT information for each expense
        expense_remarks = f"{expense.remarks if expense.remarks else ''} | \n Amount without VAT: {expense.amount_without_vat} \n VAT Amount: {expense.vat_amount} ({expense.vat_template})"
        
        # 1. GL entry for the amount without VAT (Expense Entry)
        gl_entry = {
            "doctype": "GL Entry",
            "posting_date": doc.posting_date,
            "account": expense.account_paid_to,
            "cost_center": (expense.cost_center if expense.cost_center else doc.default_cost_center),
            "project": (expense.project if expense.project else ""),
            "debit": expense.amount_without_vat,
            "credit": 0,
            "debit_in_account_currency": expense.amount_without_vat,
            "credit_in_account_currency": 0,
            "against": doc.account_paid_from,
            "voucher_type": _("Expenses Entry"),
            "voucher_no": doc.name,
            "is_opening": "No",
            "is_advance": "No",
            "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
            "company": doc.company,
            "remarks": expense_remarks  # Include VAT info in each expense's remark
        }
        gl_entries.append(gl_entry)

        # 2. Fetch VAT account and cost center from the VAT template
        if expense.vat_template:
            vat_template = frappe.get_doc("Purchase Taxes and Charges Template", expense.vat_template)
            if vat_template and vat_template.taxes:
                vat_account = vat_template.taxes[0].account_head
                vat_cost_center = vat_template.taxes[0].cost_center

                # 3. GL entry for the VAT amount
                vat_remarks = f"VAT Amount: {expense.vat_amount} | VAT Account: {vat_account} | Cost Center: {vat_cost_center}"
                vat_gl_entry = {
                    "doctype": "GL Entry",
                    "posting_date": doc.posting_date,
                    "account": vat_account,  # Use VAT account from the template
                    "cost_center": vat_cost_center,  # Use VAT cost center from the template
                    "debit": expense.vat_amount,  # Debit for VAT
                    "credit": 0,
                    "debit_in_account_currency": expense.vat_amount,
                    "credit_in_account_currency": 0,
                    "against": expense.account_paid_to,  # VAT is against the expense's account_paid_to
                    "voucher_type": _("Expenses Entry"),
                    "voucher_no": doc.name,
                    "is_opening": "No",
                    "is_advance": "No",
                    "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
                    "company": doc.company,
                    "remarks": vat_remarks  # VAT remarks
                }
                gl_entries.append(vat_gl_entry)

    # Save and submit all GL Entries
    for gl_entry in gl_entries:
        gle = frappe.new_doc("GL Entry")
        gle.update(gl_entry)
        gle.flags.ignore_permissions = 1
        gle.flags.notify_update = False
        gle.submit()




def cancel_gl_entries(doc, method):
    doc.ignore_linked_doctypes = ("GL Entry",)
    
    gl_entries = []

    # Check if the necessary fields exist to identify if it's a newer version
    is_new_version = all(
        hasattr(expense, "vat_amount") and hasattr(expense, "amount_without_vat") and hasattr(expense, "vat_template") and expense.amount_without_vat > 0
        for expense in doc.expenses
    )

    if not is_new_version:
        logger.info(f"Old version of the expenses entry")
        # If it's an older document, execute the older function logic

        paid_to_accounts = ", ".join([d.account_paid_to for d in doc.expenses])

        # Create GL entry for Account Paid From
        gl_entry = {
            "doctype": "GL Entry",
            "posting_date": doc.posting_date,
            "account": doc.account_paid_from,
            "cost_center": doc.default_cost_center,
            "debit": doc.paid_amount,
            "credit": 0,
            "debit_in_account_currency": doc.paid_amount,
            "credit_in_account_currency": 0,
            "against": paid_to_accounts,
            "voucher_type": _("Expenses Entry"),
            "voucher_no": doc.name,
            "is_opening": "No",
            "is_advance": "No",
            "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
            "company": doc.company,
            "is_cancelled": 1,
            "to_rename": 1,
            "remarks": "On Cancelled " + (doc.remarks if doc.remarks else "")
        }
        gl_entries.append(gl_entry)

        # Create GL entries for Expenses child table
        for expense in doc.expenses:
            gl_entry = {
                "doctype": "GL Entry",
                "posting_date": doc.posting_date,
                "account": expense.account_paid_to,
                "debit": 0,
                "credit": expense.amount,
                "cost_center": (expense.cost_center if expense.cost_center else doc.default_cost_center),
                "project": (expense.project if expense.project else ""),
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
                "remarks": "On Cancelled " + (expense.remarks if expense.remarks else "")
            }
            gl_entries.append(gl_entry)

    else:
        logger.info(f"New expense entry version selected")
        # New version logic - Proceed with the updated logic

        paid_to_accounts = ", ".join([d.account_paid_to for d in doc.expenses])

        # Update the remarks for cancellation with VAT details
        vat_remarks = ""
        for expense in doc.expenses:
            vat_remarks += f"Cancelled Expense: {expense.account_paid_to}, VAT: {expense.vat_amount} ({expense.vat_template})\n"

        cancel_remarks = f"On Cancelled {doc.remarks if doc.remarks else ''}\nVAT Info:\n{vat_remarks}"

        # Create GL entry for Account Paid From
        gl_entry = {
            "doctype": "GL Entry",
            "posting_date": doc.posting_date,
            "account": doc.account_paid_from,
            "cost_center": doc.default_cost_center,
            "debit": doc.paid_amount,
            "credit": 0,
            "debit_in_account_currency": doc.paid_amount,
            "credit_in_account_currency": 0,
            "against": paid_to_accounts,
            "voucher_type": _("Expenses Entry"),
            "voucher_no": doc.name,
            "is_opening": "No",
            "is_advance": "No",
            "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
            "company": doc.company,
            "is_cancelled": 1,
            "to_rename": 1,
            "remarks": cancel_remarks  # Use updated remarks with VAT info
        }
        gl_entries.append(gl_entry)

        # Create GL entries for Expenses child table and VAT
        for expense in doc.expenses:
            # Update the remarks for cancellation with VAT information
            expense_cancel_remarks = f"On Cancelled {expense.remarks if expense.remarks else ''} | \n Amount without VAT: {expense.amount_without_vat} \n VAT Amount: {expense.vat_amount} ({expense.vat_template})"
            
            # 1. GL entry for the amount without VAT (Expense Cancellation)
            gl_entry = {
                "doctype": "GL Entry",
                "posting_date": doc.posting_date,
                "account": expense.account_paid_to,
                "debit": 0,
                "credit": expense.amount_without_vat,
                "cost_center": (expense.cost_center if expense.cost_center else doc.default_cost_center),
                "project": (expense.project if expense.project else ""),
                "debit_in_account_currency": 0,
                "credit_in_account_currency": expense.amount_without_vat,
                "against": doc.account_paid_from,
                "voucher_type": _("Expenses Entry"),
                "voucher_no": doc.name,
                "is_opening": "No",
                "is_advance": "No",
                "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
                "company": doc.company,
                "is_cancelled": 1,
                "to_rename": 1,
                "remarks": expense_cancel_remarks  # Include VAT info in each expense's remark for cancellation
            }
            gl_entries.append(gl_entry)

            # 2. Fetch VAT account and cost center from the VAT template
            if expense.vat_template:
                vat_template = frappe.get_doc("Purchase Taxes and Charges Template", expense.vat_template)
                if vat_template and vat_template.taxes:
                    vat_account = vat_template.taxes[0].account_head
                    vat_cost_center = vat_template.taxes[0].cost_center

                    # 3. GL entry for the VAT amount (Cancellation)
                    vat_cancel_remarks = f"On Cancelled VAT Amount: {expense.vat_amount} | VAT Account: {vat_account} | Cost Center: {vat_cost_center}"
                    vat_gl_entry = {
                        "doctype": "GL Entry",
                        "posting_date": doc.posting_date,
                        "account": vat_account,  # Use VAT account from the template
                        "cost_center": vat_cost_center,  # Use VAT cost center from the template
                        "debit": 0,
                        "credit": expense.vat_amount,  # Credit for VAT
                        "debit_in_account_currency": 0,
                        "credit_in_account_currency": expense.vat_amount,
                        "against": expense.account_paid_to,  # VAT is against the expense's account_paid_to
                        "voucher_type": _("Expenses Entry"),
                        "voucher_no": doc.name,
                        "is_opening": "No",
                        "is_advance": "No",
                        "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
                        "company": doc.company,
                        "is_cancelled": 1,
                        "remarks": vat_cancel_remarks  # VAT cancellation remarks
                    }
                    gl_entries.append(vat_gl_entry)

    # Save and submit all GL Entries with cancellation flag
    for gl_entry in gl_entries:
        gle = frappe.new_doc("GL Entry")
        gle.update(gl_entry)
        gle.flags.ignore_permissions = 1
        gle.flags.notify_update = False
        gle.submit()

    # Set all original GL Entries as cancelled
    voucher_type = gle.voucher_type
    voucher_no = gle.voucher_no
    frappe.db.sql(
        """UPDATE `tabGL Entry` SET is_cancelled = 1,
        modified=%s, modified_by=%s
        where voucher_type=%s and voucher_no=%s and is_cancelled = 0""",
        (now(), frappe.session.user, voucher_type, voucher_no),
    )



from frappe.utils import now

def delete_gl_entries(doc, method):
    """
    Cancels and deletes GL Entries linked to the Expenses Entry before deleting the doc.
    """
    logger.info(f"Deleting GL Entries related to Expenses Entry {doc.name}")
    # Find all related GL Entries for this voucher type and number
    _delete_gl_entries("Expenses Entry", doc.name)
    
    doc.ignore_linked_doctypes = ("Gl Entry")
    
    logger.info("Ignoring the gl entries")
    # Optionally log or notify about the deletion
    frappe.msgprint(_("Cancelled and deleted GL Entries related to Expenses Entry {0}.").format(doc.name), alert=True)
