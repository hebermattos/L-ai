#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Legacy directory name is retained here solely for upgrading older installations.
source_dir="biblioteca"
destination_dir="knowledge"

if [[ ! -d "$source_dir" ]]; then
  echo "No legacy knowledge directory found; no migration needed."
  exit 0
fi

if [[ -e "$destination_dir" ]]; then
  echo "Migration aborted: $destination_dir already exists. Back up and reconcile manually." >&2
  exit 1
fi

mv -- "$source_dir" "$destination_dir"
echo "Local knowledge directory migrated to $destination_dir."
