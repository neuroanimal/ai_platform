#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_FILE="$SCRIPT_DIR/requirements-apt-packages.txt"

if [[ ! -f "$PACKAGE_FILE" ]]; then
    echo "ERROR: Missing $PACKAGE_FILE"
    exit 1
fi

INSTALLED=()
MISSING=()

while IFS= read -r package || [[ -n "$package" ]]; do
    package="${package%%#*}"
    package="$(echo "$package" | xargs)"

    [[ -z "$package" ]] && continue

    if dpkg-query -W -f='${Status}' "$package" 2>/dev/null \
        | grep -q "install ok installed"; then
        INSTALLED+=("$package")
    else
        MISSING+=("$package")
    fi
done < "$PACKAGE_FILE"

echo
echo "===== APT: ALREADY INSTALLED ====="
printf '%s\n' "${INSTALLED[@]:-None}"

echo
echo "===== APT: MISSING ====="
printf '%s\n' "${MISSING[@]:-None}"

if [[ ${#MISSING[@]} -eq 0 ]]; then
    echo
    echo "Nothing to install."
    exit 0
fi

echo
read -r -p "Install ${#MISSING[@]} missing packages? [y/N] " answer

if [[ "$answer" =~ ^[Yy]$ ]]; then
    sudo apt-get update
    sudo apt-get install -y "${MISSING[@]}"
else
    echo "Installation skipped."
fi
