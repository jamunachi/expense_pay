
import frappe
from frappe import _

def execute(filters=None):
    filters = filters or {}
    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    vat_account = filters.get("vat_account")
    cost_center = filters.get("cost_center")

    columns = [
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Voucher"), "fieldname": "voucher_no", "fieldtype": "Link", "options": "Expenses Entry", "width": 150},
        {"label": _("VAT Account"), "fieldname": "account", "fieldtype": "Link", "options": "Account", "width": 220},
        {"label": _("Cost Center"), "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 180},
        {"label": _("VAT Base (approx)"), "fieldname": "vat_base", "fieldtype": "Currency", "width": 160},
        {"label": _("VAT Amount"), "fieldname": "vat_amount", "fieldtype": "Currency", "width": 140},
        {"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Small Text", "width": 240},
    ]

    conds = ["gle.voucher_type = 'Expenses Entry'", "gle.is_cancelled = 0"]
    params = {}

    if company:
        conds.append("gle.company = %(company)s")
        params["company"] = company
    if from_date:
        conds.append("gle.posting_date >= %(from_date)s")
        params["from_date"] = from_date
    if to_date:
        conds.append("gle.posting_date <= %(to_date)s")
        params["to_date"] = to_date
    if vat_account:
        conds.append("gle.account = %(vat_account)s")
        params["vat_account"] = vat_account
    if cost_center:
        conds.append("gle.cost_center = %(cost_center)s")
        params["cost_center"] = cost_center

    sql = f"""
        select gle.posting_date, gle.voucher_no, gle.account, gle.cost_center,
               gle.debit as vat_amount,
               null as vat_base,
               gle.remarks
        from `tabGL Entry` gle
        where {' and '.join(conds)} and gle.debit > 0 and gle.account in (
            select distinct account_head from `tabPurchase Taxes and Charges` ptc
        )
        order by gle.posting_date, gle.voucher_no
    """
    data = frappe.db.sql(sql, params, as_dict=True)

    return columns, data
