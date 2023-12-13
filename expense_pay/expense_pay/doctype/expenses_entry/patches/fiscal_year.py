import frappe
from frappe.utils import getdate, logger

logger.set_log_level("DEBUG")
logger = frappe.logger("fiscal_year_patch", allow_site=True, file_count=1)

def execute():
    # Fetch all GL Entry documents that have a voucher_no containing "ACC-JV"
    try:
        gl_entries = frappe.get_all("GL Entry", filters={"voucher_type": "Expenses Entry", "voucher_no": ("like", "ACC-PAY-%")}, fields=["name", "creation", "fiscal_year"])

        for entry in gl_entries:
            # Extract the year from the creation date
            try:
                creation_year = getdate(entry.creation).year

                # Check if the fiscal year matches the creation year
                if str(creation_year) != entry.fiscal_year:
                    # Update the fiscal_year if it doesn't match
                    frappe.db.set_value("GL Entry", entry.name, "fiscal_year", str(creation_year), update_modified=False)
                    logger.info(f"Updated fiscal year for GL Entry {entry.name} to {creation_year}")
                    print(f"Updated fiscal year for GL Entry {entry.name} to {creation_year}")
                    
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"Error: {e}")
                
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}")

    # Commit the changes to the database
    frappe.db.commit()
