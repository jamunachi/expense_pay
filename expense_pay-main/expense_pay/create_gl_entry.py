import frappe
from frappe import _
from frappe.utils import  now, logger, flt
from erpnext.accounts.utils import _delete_gl_entries

logger.set_log_level("DEBUG")
logger = frappe.logger("expensepay", file_count=1, allow_site=True)

# Cache settings
_SETTINGS = None
def _ep_get_settings():
    global _SETTINGS
    if _SETTINGS is None:
        try:
            _SETTINGS = frappe.get_single("Expense Entry Settings")
        except Exception:
            class _Fallback: pass
            _SETTINGS = _Fallback()
            # defaults
            _SETTINGS.enable_debug_logs = 0
            _SETTINGS.log_to_error_log = 1
            _SETTINGS.vat_use_row_cc = 1
            _SETTINGS.fallback_header_cc = 1
            _SETTINGS.enforce_header_cc_credit = 1
            _SETTINGS.enforce_row_cc_debit = 1
            _SETTINGS.gl_amount_precision = None
            _SETTINGS.only_leaf_accounts = 1
            _SETTINGS.only_leaf_cost_centers = 1
            _SETTINGS.allow_multi_tax_per_row = 0
    return _SETTINGS

# Helper: get currency precision for GL amounts once
try:
    _GL_PREC = frappe.get_precision("GL Entry", "debit") or 2
except Exception:
    _GL_PREC = 2

def _ep_round(v):
    try:
        s = _ep_get_settings()
        prec = getattr(s, "gl_amount_precision", None) or _GL_PREC
    except Exception:
        prec = _GL_PREC
    return flt(v or 0, prec)

@frappe.whitelist()
def create_gl_entries(doc, method):
    settings = _ep_get_settings()
    try:
        logger.set_log_level("DEBUG" if getattr(settings, "enable_debug_logs", 0) else "INFO")
    except Exception:
        pass
    try:
        # MAIN LOGIC START
        _ep_validate_leaf(doc)
    gl_entries = []

    # Create GL entry for Account Paid From
    paid_to_accounts = ", ".join([d.account_paid_to for d in doc.expenses])
    
    # Update the remarks with VAT details
    vat_remarks = ""
    for expense in doc.expenses:
        vat_remarks += f"Expense: {expense.account_paid_to}, VAT: {expense.vat_amount} ({expense.vat_template})\n"

    main_remarks = f"{doc.remarks}\nVAT Info:\n{vat_remarks}"
    
    # GL entry for the account paid from
    gl_entry = {
        "doctype": "GL Entry",
        "posting_date": doc.posting_date,
        "account": doc.account_paid_from,
        "cost_center": (doc.default_cost_center if getattr(_ep_get_settings(), "enforce_header_cc_credit", 1) else ""),
        "debit": _ep_round(0),
        "credit": _ep_round(doc.paid_amount),
        "debit_in_account_currency": _ep_round(0),
        "credit_in_account_currency": _ep_round(doc.paid_amount),
        "against": paid_to_accounts,
        "voucher_type": "Expenses Entry",
        "voucher_no": doc.name,
        "is_opening": "No",
        "is_advance": "No",
        "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
        "company": doc.company,
        "remarks": main_remarks
    }
    gl_entries.append(gl_entry)

    # Create GL entries for each expense and VAT
    for expense in doc.expenses:
        expense_remarks = f"{expense.remarks or ''} | Amount without VAT: {expense.amount_without_vat} | VAT Amount: {expense.vat_amount} ({expense.vat_template})"
        logger.info(f"Amount without vat : {expense.amount_without_vat}\n")
        # GL entry for the amount without VAT
        gl_entry = {
            "doctype": "GL Entry",
            "posting_date": doc.posting_date,
            "account": expense.account_paid_to,
            "cost_center": expense.cost_center or doc.default_cost_center,
            "project": expense.project or "",
            "debit": _ep_round(expense.amount_without_vat),
            "credit": _ep_round(0),
            "debit_in_account_currency": _ep_round(expense.amount_without_vat),
            "credit_in_account_currency": _ep_round(0),
            "against": doc.account_paid_from,
            "voucher_type": "Expenses Entry",
            "voucher_no": doc.name,
            "is_opening": "No",
            "is_advance": "No",
            "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
            "company": doc.company,
            "remarks": expense_remarks
        }
        gl_entries.append(gl_entry)

        # GL entry for VAT amount
        if expense.vat_template and (expense.vat_amount > 0):
            try:
                vat_template = frappe.get_doc("Purchase Taxes and Charges Template", expense.vat_template)
            except Exception:
                vat_template = None
            for _gle in _ep_build_vat_gl_entries(doc, expense, vat_template, _ep_get_settings(), is_cancellation=False):
                gl_entries.append(_gle)

        # Create GL entries for Expenses child table
        for expense in doc.expenses:
            gl_entry = {
                "doctype": "GL Entry",
                "posting_date": doc.posting_date,
                "account": expense.account_paid_to,
                "debit": _ep_round(0),
                "credit": _ep_round(expense.amount),
                "cost_center": (expense.cost_center if getattr(_ep_get_settings(), "enforce_row_cc_debit", 1) else doc.default_cost_center) or doc.default_cost_center,
                "project": (expense.project if expense.project else ""),
                "debit_in_account_currency": _ep_round(0),
                "credit_in_account_currency": _ep_round(expense.amount),
                "against": doc.account_paid_from,
                "voucher_type": "Expenses Entry",
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
            "debit": _ep_round(doc.paid_amount),
            "credit": _ep_round(0),
            "debit_in_account_currency": _ep_round(doc.paid_amount),
            "credit_in_account_currency": _ep_round(0),
            "against": paid_to_accounts,
            "voucher_type": "Expenses Entry",
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
                "debit": _ep_round(0),
                "credit": _ep_round(expense.amount_without_vat),
                "cost_center": (expense.cost_center if getattr(_ep_get_settings(), "enforce_row_cc_debit", 1) else doc.default_cost_center) or doc.default_cost_center,
                "project": (expense.project if expense.project else ""),
                "debit_in_account_currency": _ep_round(0),
                "credit_in_account_currency": _ep_round(expense.amount_without_vat),
                "against": doc.account_paid_from,
                "voucher_type": "Expenses Entry",
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
                vat_cost_center = expense.cost_center or doc.default_cost_center or ""

                    # 3. GL entry for the VAT amount (Cancellation)
                    vat_cancel_remarks = f"On Cancelled VAT Amount: {expense.vat_amount} | VAT Account: {vat_account} | Cost Center: {vat_cost_center}"
                    vat_gl_entry = {
                        "doctype": "GL Entry",
                        "posting_date": doc.posting_date,
                        "account": vat_account,  # Use VAT account from the template
                        "cost_center": vat_cost_center,  # Use VAT cost center from the template
                        "debit": _ep_round(0),
                        "credit": _ep_round(expense.vat_amount),  # Credit for VAT
                        "debit_in_account_currency": _ep_round(0),
                        "credit_in_account_currency": _ep_round(expense.vat_amount),
                        "against": expense.account_paid_to,  # VAT is against the expense's account_paid_to
                        "voucher_type": "Expenses Entry",
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
    
    doc.ignore_linked_doctypes = ("GL Entry",)
    
    logger.info("Ignoring the gl entries")
    # Optionally log or notify about the deletion
    frappe.msgprint(_("Cancelled and deleted GL Entries related to Expenses Entry {0}.").format(doc.name), alert=True)


@frappe.whitelist()
def sync_missing_gl_entries():
    missing_entries = []
    validation_errors = []

    # Log the start of the function
    logger.info("Starting sync_missing_gl_entries function")

    # Fetch submitted Expenses Entries
    expenses_entries = frappe.get_all("Expenses Entry", filters={"docstatus": 1}, fields=["name"])
    logger.info(f"Fetched {len(expenses_entries)} submitted Expenses Entries")

    for entry in expenses_entries:
        # Fetch the Expenses Entry document
        doc = frappe.get_doc("Expenses Entry", entry.name)
        logger.info(f"Processing Expenses Entry: {doc.name}")

        # Update amounts if amount_without_vat and vat_amount are zero
        for expense in doc.expenses:
            if expense.amount_without_vat == 0 and expense.vat_amount == 0 and expense.amount > 0:
                logger.info(f"Updating amount_without_vat for row #{expense.idx} in doc {doc.name}")
                expense.amount_without_vat = expense.amount

        # Save the updated document before creating GL Entries
        try:
            doc.save()
            frappe.db.commit()
            logger.info(f"Saved updated document {doc.name}")
        except Exception as e:
            logger.error(f"Error saving document {doc.name}: {e}")
            validation_errors.append(f"Error saving document {doc.name}: {str(e)}")
            continue


        # Step 1: Validate all rows in the expenses child table
        doc_validation_errors = []
        for expense in doc.expenses:
            logger.info(f"Validating row #{expense.idx} in doc {doc.name}")
            if expense.amount != expense.amount_without_vat + expense.vat_amount:
                error_message = _(
                    "Doc {0}, Row #{1}: Amount ({2}) does not equal Amount Without VAT ({3}) + VAT Amount ({4}) <br><br>"
                ).format(
                    doc.name,
                    expense.idx,
                    expense.amount,
                    expense.amount_without_vat,
                    expense.vat_amount
                )
                logger.info(f"Validation error found: {error_message}")
                doc_validation_errors.append(error_message)

        # If there are validation errors for this document, collect them and skip GL Entry creation
        if doc_validation_errors:
            logger.info(f"Validation errors found in doc {doc.name}, skipping GL Entry creation")
            validation_errors.extend(doc_validation_errors)
            continue  # Skip to the next document

        # Check if GL Entries exist for this Expenses Entry
        gl_entries = frappe.get_all("GL Entry", filters={"voucher_type": "Expenses Entry", "voucher_no": entry.name})
        logger.info(f"GL Entries found for {doc.name}: {len(gl_entries)}")

        if not gl_entries:
            logger.info(f"No GL Entries found for {doc.name}, creating GL Entries")

            # Call the existing function to create GL Entries
            try:
                create_gl_entries(doc, "on_submit")
                logger.info(f"GL Entries successfully created for {doc.name}")
                missing_entries.append(doc.name)
            except Exception as e:
                logger.error(f"Error creating GL Entries for document {doc.name}: {e}")
                validation_errors.append(f"Error creating GL Entries for document {doc.name}: {str(e)}")

    # After processing all documents, throw an error if any validation errors were collected
    if validation_errors:
        logger.info("Validation errors encountered during the process")
        frappe.throw(
            _("The following validation errors were found:\n\n{0}").format("\n".join(validation_errors)),
            title=_("Validation Errors Found")
        )

    logger.info(f"GL Entries created for the following documents: {missing_entries}")

    # Return the list of entries where GL Entries were created
    return missing_entries


@frappe.whitelist()
def find_miscalculated_amounts():
    miscalculated_entries = []

    # Fetch submitted Expenses Entries
    expenses_entries = frappe.get_all("Expenses Entry", filters={"docstatus": 1}, fields=["name"])

    for entry in expenses_entries:
        doc = frappe.get_doc("Expenses Entry", entry.name)
        for expense in doc.expenses:
            if expense.amount != expense.amount_without_vat + expense.vat_amount:
                miscalculated_entries.append(entry.name)
                break  # No need to check further rows if one is already miscalculated

    return miscalculated_entries

def _ep_validate_leaf(doc):
    s = _ep_get_settings()
    if int(getattr(s, "only_leaf_accounts", 0)):
        if getattr(doc, "account_paid_from", None):
            if frappe.db.get_value("Account", doc.account_paid_from, "is_group"):
                frappe.throw(_("Account Paid From must be a leaf account."))
        for d in getattr(doc, "expenses", []) or []:
            if d.account_paid_to and frappe.db.get_value("Account", d.account_paid_to, "is_group"):
                frappe.throw(_("Row {0}: Account must be a leaf account.").format(d.idx))
    if int(getattr(s, "only_leaf_cost_centers", 0)):
        if getattr(doc, "default_cost_center", None):
            if frappe.db.get_value("Cost Center", doc.default_cost_center, "is_group"):
                frappe.throw(_("Default Cost Center must be a leaf node."))
        for d in getattr(doc, "expenses", []) or []:
            if d.cost_center and frappe.db.get_value("Cost Center", d.cost_center, "is_group"):
                frappe.throw(_("Row {0}: Cost Center must be a leaf node.").format(d.idx))

def _ep_build_vat_gl_entries(doc, expense, vat_template_doc, settings, is_cancellation=False):
    gls = []
    taxes = (vat_template_doc.taxes or []) if vat_template_doc else []
    if not taxes:
        return gls
    vat_cc = (expense.cost_center if getattr(settings, "vat_use_row_cc", 1) else None)              or (doc.default_cost_center if getattr(settings, "fallback_header_cc", 1) else None)              or ""
    allow_multi = int(getattr(settings, "allow_multi_tax_per_row", 0) or 0)
    if allow_multi and len(taxes) > 1:
        rates = [abs(getattr(t, "rate", 0) or 0) for t in taxes]
        total_rate = sum(rates) or 0
        if total_rate > 0:
            for t, r in zip(taxes, rates):
                part = (expense.vat_amount or 0) * (r / total_rate)
                gls.append({
                    "doctype": "GL Entry",
                    "posting_date": doc.posting_date,
                    "account": t.account_head,
                    "cost_center": vat_cc,
                    "debit": _ep_round(0 if is_cancellation else part),
                    "credit": _ep_round(part if is_cancellation else 0),
                    "debit_in_account_currency": _ep_round(0 if is_cancellation else part),
                    "credit_in_account_currency": _ep_round(part if is_cancellation else 0),
                    "against": expense.account_paid_to,
                    "voucher_type": "Expenses Entry",
                    "voucher_no": doc.name,
                    "is_opening": "No",
                    "is_advance": "No",
                    "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
                    "company": doc.company,
                })
            return gls
    # fallback single
    vat_account = taxes[0].account_head
    amount = expense.vat_amount or 0
    gls.append({
        "doctype": "GL Entry",
        "posting_date": doc.posting_date,
        "account": vat_account,
        "cost_center": vat_cc,
        "debit": _ep_round(0 if is_cancellation else amount),
        "credit": _ep_round(amount if is_cancellation else 0),
        "debit_in_account_currency": _ep_round(0 if is_cancellation else amount),
        "credit_in_account_currency": _ep_round(amount if is_cancellation else 0),
        "against": expense.account_paid_to,
        "voucher_type": "Expenses Entry",
        "voucher_no": doc.name,
        "is_opening": "No",
        "is_advance": "No",
        "fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
        "company": doc.company,
    })
    return gls

@frappe.whitelist()
def simulate_gl_entries(doc):
    if isinstance(doc, str):
        doc = frappe.parse_json(doc)
    doc = frappe._dict(doc)
    settings = _ep_get_settings()
    gl = []
    def push(account, debit=0, credit=0, cost_center=None, project=None, remarks=None):
        gl.append({
            "account": account,
            "debit": _ep_round(debit),
            "credit": _ep_round(credit),
            "cost_center": cost_center or "",
            "project": project or "",
            "remarks": remarks or ""
        })
    if getattr(doc, "account_paid_from", None):
        cc = (doc.default_cost_center if getattr(settings, "enforce_header_cc_credit", 1) else "")
        paid_to_accounts = ", ".join([d.get("account_paid_to") for d in doc.get("expenses", []) if d.get("account_paid_to")])
        push(doc.account_paid_from, debit=0, credit=doc.paid_amount, cost_center=cc, remarks=paid_to_accounts)
    for row in doc.get("expenses", []) or []:
        row = frappe._dict(row)
        cc = (row.cost_center if getattr(settings, "enforce_row_cc_debit", 1) else doc.default_cost_center) or doc.default_cost_center
        push(row.account_paid_to, debit=row.amount_without_vat, credit=0, cost_center=cc, project=row.get("project"))
        if row.get("vat_template") and (row.get("vat_amount") or 0) > 0:
            try:
                vt = frappe.get_doc("Purchase Taxes and Charges Template", row.vat_template)
            except Exception:
                vt = None
            allow_multi = int(getattr(settings, "allow_multi_tax_per_row", 0) or 0)
            cc_vat = (row.cost_center if getattr(settings, "vat_use_row_cc", 1) else None) or (doc.default_cost_center if getattr(settings, "fallback_header_cc", 1) else None)
            taxes = (vt.taxes or []) if vt else []
            if allow_multi and len(taxes) > 1:
                rates = [abs(getattr(t, "rate", 0) or 0) for t in taxes]
                tr = sum(rates) or 0
                if tr > 0:
                    for t, r in zip(taxes, rates):
                        part = (row.vat_amount or 0) * (r / tr)
                        push(t.account_head if getattr(t, "account_head", None) else "(VAT)", debit=part, credit=0, cost_center=cc_vat)
                    continue
            # fallback single
            vat_account = taxes[0].account_head if taxes else "(VAT)"
            push(vat_account, debit=row.vat_amount, credit=0, cost_center=cc_vat)
    total_debit = _ep_round(sum(x["debit"] for x in gl))
    total_credit = _ep_round(sum(x["credit"] for x in gl))
    return {"rows": gl, "total_debit": total_debit, "total_credit": total_credit, "balanced": abs(total_debit - total_credit) < (10 ** -(_GL_PREC))}
