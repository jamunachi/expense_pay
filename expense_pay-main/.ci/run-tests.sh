
#!/usr/bin/env bash
set -euo pipefail

SITE="${1:-test-site.local}"

echo ">> Running tests on site: $SITE"

bench --site "$SITE" reinstall --yes
bench --site "$SITE" install-app expense_pay
bench --site "$SITE" run-tests --app expense_pay
