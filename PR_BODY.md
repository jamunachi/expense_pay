
# Expense Pay: v0.3.0 — Reports, Roles, Import, Tests

## What’s new
- Reports
  - Expense Allocation by Cost Center
  - Expense VAT Ledger
- Role-based rules (submit, cancel, import, override filters)
- Import + Dry Run + validations
- Automated tests (starter)
- Includes earlier: multi-tax toggle, GL Preview, picker filters, rounding & logging, VAT row CC

## Deploy
```bash
cd ~/frappe-bench/apps/expense_pay
git checkout -b release/v0.3.0
git apply /path/to/expense_pay_PR_v0.3.0.patch
git status
git add -A
git commit -m "feat: reports, roles, importer, tests; plus multi-tax toggle and GL preview"
git push origin release/v0.3.0
# optional tag
git tag -a v0.3.0 -m "v0.3.0"
git push origin v0.3.0

cd ~/frappe-bench
bench --site <your.site> migrate
bench clear-cache
```
