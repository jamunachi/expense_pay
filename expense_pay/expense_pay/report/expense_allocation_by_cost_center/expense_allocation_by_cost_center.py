
import frappe
from frappe import _

def execute(filters=None):
    filters = filters or {}
    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    cc = filters.get("cost_center")
    project = filters.get("project")

    columns = [
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Voucher"), "fieldname": "voucher_no", "fieldtype": "Link", "options": "Expenses Entry", "width": 150},
        {"label": _("Row"), "fieldname": "idx", "fieldtype": "Int", "width": 60},
        {"label": _("Expense Account"), "fieldname": "account", "fieldtype": "Link", "options": "Account", "width": 200},
        {"label": _("Cost Center"), "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 180},
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140},
        {"label": _("Amount (w/o VAT)"), "fieldname": "amount_wo_vat", "fieldtype": "Currency", "width": 150},
        {"label": _("VAT Amount"), "fieldname": "vat_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "width": 140},
        {"label": _("User"), "fieldname": "owner", "fieldtype": "Data", "width": 120},
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
    if cc:
        conds.append("gle.cost_center = %(cc)s")
        params["cc"] = cc
    if project:
        conds.append("gle.project = %(project)s")
        params["project"] = project

    sql = f"""
        select gle.posting_date, gle.voucher_no, ged.idx, gle.account, gle.cost_center, gle.project,
               gle.debit as amount_wo_vat, 0 as vat_amount, gle.debit as total, doc.owner, gle.remarks
        from `tabGL Entry` gle
        left join `tabExpenses Entry` doc on doc.name = gle.voucher_no
        left join `tabExpenses` ged on ged.parent = gle.voucher_no and ged.account_paid_to = gle.account
        where {' and '.join(conds)} and gle.debit > 0
        union all
        select gle.posting_date, gle.voucher_no, 0 as idx, gle.account, gle.cost_center, gle.project,
               0 as amount_wo_vat, gle.debit as vat_amount, gle.debit as total, doc.owner, gle.remarks
        from `tabGL Entry` gle
        left join `tabExpenses Entry` doc on doc.name = gle.voucher_no
        where {' and '.join(conds)} and gle.debit > 0 and gle.account in (
            select distinct account_head from `tabPurchase Taxes and Charges` ptc
        )
    """
    data = frappe.db.sql(sql, params, as_dict=True)

    return columns, data
