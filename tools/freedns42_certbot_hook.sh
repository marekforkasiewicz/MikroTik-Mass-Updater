#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK="$ROOT_DIR/tools/freedns42_acme_hook.sh"

ACTION="${1:-}"
DOMAIN="${CERTBOT_DOMAIN:-}"
VALIDATION="${CERTBOT_VALIDATION:-}"

if [[ -z "$ACTION" || -z "$DOMAIN" || -z "$VALIDATION" ]]; then
  echo "usage: freedns42_certbot_hook.sh <present|cleanup> with CERTBOT_DOMAIN and CERTBOT_VALIDATION in env" >&2
  exit 1
fi

exec /bin/bash "$HOOK" "$ACTION" "$DOMAIN" "$VALIDATION"
