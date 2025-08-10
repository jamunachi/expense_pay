
import frappe, csv, io
from frappe import _
from .permissions import can_import
from .create_gl_entry import _ep_round, _ep_get_settings
from frappe.utils import flt

TEMPLATE_HEADERS = [
    "company","posting_date","account_paid_from","default_cost_center","paid_amount","remarks",
    "row_no","account_paid_to","row_cost_center","amount_without_vat","vat_template","vat_amount","project","row_remarks"
]

@frappe.whitelist()
def download_template():
    s = io.StringIO()
    w = csv.writer(s)
    w.writerow(TEMPLATE_HEADERS)
    return s.getvalue()

def _parse_csv(content: str):
    rows = []
    r = csv.DictReader(io.StringIO(content))
    for i, row in enumerate(r, start=1):
        rows.append({k: (row.get(k) or "").strip() for k in TEMPLATE_HEADERS})
    return rows

def _validate_leaf(name, doctype):
    is_group = frappe.db.get_value(doctype, name, "is_group")
    return not is_group

@frappe.whitelist()
def import_expenses(csv_content: str, dry_run: int = 1):
    if not can_import():
        frappe.throw(_("You are not allowed to import Expenses."))

    data = _parse_csv(csv_content)
    errors = []
    rows = []
    header = None
    settings = _ep_get_settings()

    for d in data:
        if not header:
            header = {
                "company": d["company"],
                "posting_date": d["posting_date"],
                "account_paid_from": d["account_paid_from"],
                "default_cost_center": d["default_cost_center"],
                "paid_amount": flt(d["paid_amount"]),
                "remarks": d["remarks"]
            }
        if d["account_paid_to"]:
            rows.append({
                "account_paid_to": d["account_paid_to"],
                "cost_center": d["row_cost_center"],
                "amount_without_vat": flt(d["amount_without_vat"] or 0),
                "vat_template": d["vat_template"],
                "vat_amount": flt(d["vat_amount"] or 0),
                "project": d["project"],
                "remarks": d["row_remarks"],
            })

    if not header or not rows:
        errors.append(_("No data rows found."))

    if int(getattr(settings, "only_leaf_accounts", 0)):
        if header.get("account_paid_from") and not _validate_leaf(header["account_paid_from"], "Account"):
            errors.append(_("Account Paid From must be a leaf account."))
        for i, r in enumerate(rows, start=1):
            if r["account_paid_to"] and not _validate_leaf(r["account_paid_to"], "Account"):
                errors.append(_("Row {0}: Account must be a leaf account.").format(i))
    if int(getattr(settings, "only_leaf_cost_centers", 0)):
        if header.get("default_cost_center") and not _validate_leaf(header["default_cost_center"], "Cost Center"):
            errors.append(_("Default Cost Center must be leaf."))
        for i, r in enumerate(rows, start=1):
            if r["cost_center"] and not _validate_leaf(r["cost_center"], "Cost Center"):
                errors.append(_("Row {0}: Cost Center must be leaf.").format(i))

    expected = _ep_round(sum((r["amount_without_vat"] + r.get("vat_amount", 0)) for r in rows))
    if _ep_round(header.get("paid_amount", 0)) != expected:
        errors.append(_("Paid Amount must equal total of rows (Amount w/o VAT + VAT). Expected {0}").format(expected))

    if errors:
        return {"ok": False, "errors": errors}

    if int(dry_run or 1):
        return {"ok": True, "dry_run": True, "header": header, "rows": rows}

    doc = frappe.new_doc("Expenses Entry")
    doc.update({
        "company": header["company"],
        "posting_date": header["posting_date"],
        "account_paid_from": header["account_paid_from"],
        "default_cost_center": header["default_cost_center"],
        "paid_amount": header["paid_amount"],
        "remarks": header["remarks"],
        "expenses": []
    })
    for r in rows:
        doc.append("expenses", {
            "account_paid_to": r["account_paid_to"],
            "cost_center": r["cost_center"],
            "amount_without_vat": r["amount_without_vat"],
            "vat_template": r["vat_template"],
            "vat_amount": r["vat_amount"],
            "project": r["project"],
            "remarks": r["remarks"]
        })
    doc.insert()
    doc.submit()
    return {"ok": True, "dry_run": False, "voucher": doc.name}


def _split_lines(val):
    if not val: return []
    out = []
    for line in val.splitlines():
        for p in line.split(','):
            p = (p or '').strip()
            if p: out.append(p)
    return out

def _get_allowed_account_types(settings, kind: str):
    if kind == "debit":
        return set(_split_lines(getattr(settings, "debit_account_types", "")))
    if kind == "credit":
        return set(_split_lines(getattr(settings, "credit_account_types", "")))
    return set()
