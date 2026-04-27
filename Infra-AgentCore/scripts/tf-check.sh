#!/usr/bin/env bash
# tf-check.sh — fmt + validate de todo el repo Infra-AgentCore.
# Uso:
#   scripts/tf-check.sh           # fmt -check + validate (falla si algo no está canónico)
#   scripts/tf-check.sh fix       # tofu fmt en lugar de fmt -check (auto-fix)
#   scripts/tf-check.sh fmt-only  # solo fmt -check, sin validate
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

# Detectar binary: preferir tofu, fallback terraform
if command -v tofu >/dev/null 2>&1; then
  TF=tofu
elif command -v terraform >/dev/null 2>&1; then
  TF=terraform
else
  echo "ERROR: ni tofu ni terraform están instalados (brew install opentofu)" >&2
  exit 127
fi

mode="${1:-check}"
fail=0

echo "==> $TF fmt"
case "$mode" in
  fix)
    "$TF" fmt -recursive "$ROOT"
    ;;
  *)
    if ! "$TF" fmt -check -recursive "$ROOT"; then
      echo "FAIL: archivos fuera de formato canónico (corre 'scripts/tf-check.sh fix')" >&2
      fail=1
    fi
    ;;
esac

if [ "$mode" = "fmt-only" ]; then
  exit "$fail"
fi

echo "==> $TF validate (init -backend=false en cada subdir)"
for dir in compositions/* foundation/*; do
  [ -d "$dir" ] || continue
  ls "$dir"/*.tf >/dev/null 2>&1 || continue
  echo "    -> $dir"
  if ! (cd "$dir" && "$TF" init -backend=false -input=false -no-color >/dev/null 2>&1 && "$TF" validate -no-color); then
    echo "FAIL: $dir" >&2
    fail=1
  fi
done

if [ "$fail" -eq 0 ]; then
  echo "==> OK"
fi
exit "$fail"
