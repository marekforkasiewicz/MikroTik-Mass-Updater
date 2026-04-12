#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUTH_HOOK="$ROOT_DIR/tools/freedns42_certbot_hook.sh"
IMPORTER="$ROOT_DIR/tools/npm_certificate_import.py"

CERTBOT_EMAIL="${CERTBOT_EMAIL:-admin@efork.pl}"
CERTBOT_CERT_NAME="${CERTBOT_CERT_NAME:-wildcard-efork.pl}"
CERTBOT_CONFIG_DIR="${CERTBOT_CONFIG_DIR:-/root/letsencrypt}"
CERTBOT_WORK_DIR="${CERTBOT_WORK_DIR:-/root/letsencrypt/work}"
CERTBOT_LOGS_DIR="${CERTBOT_LOGS_DIR:-/root/letsencrypt/logs}"
NPM_API_URL="${NPM_API_URL:-http://127.0.0.1:81/api}"
NPM_IDENTITY="${NPM_IDENTITY:-admin@efork.pl}"
NPM_SECRET="${NPM_SECRET:-Kolo12wd_}"
NPM_CERT_NAME="${NPM_CERT_NAME:-Wildcard efork.pl}"
NPM_DOMAINS="${NPM_DOMAINS:-efork.pl,*.efork.pl}"
NPM_PROXY_HOST_ID="${NPM_PROXY_HOST_ID:-1}"
CERTBOT_SERVER="${CERTBOT_SERVER:-}"
CERTBOT_STAGING="${CERTBOT_STAGING:-0}"
ASSIGN_TO_PROXY="${ASSIGN_TO_PROXY:-0}"

mkdir -p "$CERTBOT_CONFIG_DIR" "$CERTBOT_WORK_DIR" "$CERTBOT_LOGS_DIR"

certbot_args=(
  certbot certonly
  --manual
  --preferred-challenges dns
  --manual-auth-hook "/bin/bash $AUTH_HOOK present"
  --manual-cleanup-hook "/bin/bash $AUTH_HOOK cleanup"
  --agree-tos
  --non-interactive
  --email "$CERTBOT_EMAIL"
  --config-dir "$CERTBOT_CONFIG_DIR"
  --work-dir "$CERTBOT_WORK_DIR"
  --logs-dir "$CERTBOT_LOGS_DIR"
  --cert-name "$CERTBOT_CERT_NAME"
  --keep-until-expiring
  -d efork.pl
  -d '*.efork.pl'
)

if [[ -n "$CERTBOT_SERVER" ]]; then
  certbot_args+=(--server "$CERTBOT_SERVER")
fi

if [[ "$CERTBOT_STAGING" == "1" ]]; then
  certbot_args+=(--test-cert)
fi

"${certbot_args[@]}"

live_dir="$CERTBOT_CONFIG_DIR/live/$CERTBOT_CERT_NAME"
cert="$live_dir/cert.pem"
key="$live_dir/privkey.pem"
chain="$live_dir/chain.pem"

import_args=(
  python3 "$IMPORTER"
  --npm-url "$NPM_API_URL"
  --identity "$NPM_IDENTITY"
  --secret "$NPM_SECRET"
  --nice-name "$NPM_CERT_NAME"
  --domains "$NPM_DOMAINS"
  --cert "$cert"
  --key "$key"
  --chain "$chain"
)

if [[ "$ASSIGN_TO_PROXY" == "1" ]]; then
  import_args+=(--assign-proxy-host-id "$NPM_PROXY_HOST_ID")
fi

"${import_args[@]}"
