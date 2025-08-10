
import frappe
from frappe import _

def _allowed_roles():
    s = frappe.get_single("Expense Entry Settings")
    roles = [r.role for r in (s.allowed_roles or []) if getattr(r, "role", None)]
    return set(roles or [])

def _user_has_allowed_role():
    user_roles = set(frappe.get_roles())
    allowed = _allowed_roles()
    if not allowed:
        return True
    return bool(user_roles & allowed)

def enforce_submit(doc, method):
    s = frappe.get_single("Expense Entry Settings")
    if int(s.restrict_submit or 0):
        if not _user_has_allowed_role():
            frappe.throw(_("You are not allowed to Submit this document. Please contact your administrator."))

def enforce_cancel(doc, method):
    s = frappe.get_single("Expense Entry Settings")
    if int(s.restrict_cancel or 0):
        if not _user_has_allowed_role():
            frappe.throw(_("You are not allowed to Cancel this document. Please contact your administrator."))

def can_override_filters() -> bool:
    s = frappe.get_single("Expense Entry Settings")
    if not int(s.restrict_override_filters or 0):
        return True
    return _user_has_allowed_role()

def can_import() -> bool:
    s = frappe.get_single("Expense Entry Settings")
    if not int(s.restrict_import or 0):
        return True
    return _user_has_allowed_role()
