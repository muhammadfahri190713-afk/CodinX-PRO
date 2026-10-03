#!/usr/bin/env bash
# Pasang pre-commit hook: blokir commit yang berisi rahasia / file .env. Pakai: bash scripts/install-git-hooks.sh
set -euo pipefail
root="$(git rev-parse --show-toplevel)"
install -m 755 "$root/scripts/pre-commit" "$root/.git/hooks/pre-commit"
echo "✓ pre-commit terpasang di $root/.git/hooks/pre-commit"
