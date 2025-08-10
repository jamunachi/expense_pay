
import frappe

def ensure_company(name="TST Co"):
    if not frappe.db.exists("Company", name):
        frappe.get_doc({
            "doctype": "Company",
            "company_name": name,
            "abbr": "TST",
            "default_currency": "SAR",
            "country": "Saudi Arabia"
        }).insert()
    return name

def ensure_account(name, company, parent=None, account_type=None, is_group=0):
    if not frappe.db.exists("Account", {"company": company, "name": name}):
        doc = frappe.get_doc({
            "doctype": "Account",
            "account_name": name.split(" - ")[0],
            "company": company,
            "parent_account": parent or frappe.db.get_value("Account", {"company": company, "is_group": 1}, "name"),
            "is_group": is_group,
            "account_type": account_type
        })
        doc.insert()
        # rename to include company abbr if not already
        if " - " not in name and doc.name != name:
            frappe.rename_doc("Account", doc.name, name, force=True)
    return name

def ensure_cost_center(name, company, parent=None, is_group=0):
    if not frappe.db.exists("Cost Center", {"company": company, "name": name}):
        doc = frappe.get_doc({
            "doctype": "Cost Center",
            "cost_center_name": name.split(" - ")[0],
            "company": company,
            "parent_cost_center": parent or frappe.db.get_value("Cost Center", {"company": company, "is_group": 1}, "name"),
            "is_group": is_group,
        })
        doc.insert()
        if " - " not in name and doc.name != name:
            frappe.rename_doc("Cost Center", doc.name, name, force=True)
    return name

def ensure_vat_template(name, account, rate=15.0):
    # Create a simple Purchase Taxes and Charges Template
    if not frappe.db.exists("Purchase Taxes and Charges Template", name):
        doc = frappe.get_doc({
            "doctype": "Purchase Taxes and Charges Template",
            "title": name,
            "company": frappe.defaults.get_user_default("company"),
            "taxes": [{
                "category": "Total",
                "charge_type": "On Net Total",
                "account_head": account,
                "rate": rate
            }]
        })
        doc.insert()
    return name
