#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELPER="$ROOT_DIR/tools/freedns42_zone_helper.py"

FREEDNS42_ZONE="${FREEDNS42_ZONE:-efork.pl}"
FREEDNS42_PROPAGATION_SECONDS="${FREEDNS42_PROPAGATION_SECONDS:-900}"
FREEDNS42_PROPAGATION_INTERVAL_SECONDS="${FREEDNS42_PROPAGATION_INTERVAL_SECONDS:-15}"
FREEDNS42_DNS_SERVER="${FREEDNS42_DNS_SERVER:-fns1.42.pl}"
FREEDNS42_RECURSIVE_TIMEOUT_SECONDS="${FREEDNS42_RECURSIVE_TIMEOUT_SECONDS:-300}"
FREEDNS42_RECURSIVE_DNS_SERVERS="${FREEDNS42_RECURSIVE_DNS_SERVERS:-1.1.1.1 8.8.8.8}"

if [[ ! -f "$HELPER" ]]; then
  echo "helper not found: $HELPER" >&2
  exit 1
fi

record_name_for_domain() {
  local domain="$1"
  if [[ "$domain" == \*.* ]]; then
    domain="${domain#*.}"
  fi
  if [[ "$domain" == "$FREEDNS42_ZONE" ]]; then
    echo "_acme-challenge"
  else
    echo "_acme-challenge.${domain%.$FREEDNS42_ZONE}"
  fi
}

record_fqdn_for_domain() {
  local domain="$1"
  local record_name
  record_name="$(record_name_for_domain "$domain")"
  echo "${record_name}.${FREEDNS42_ZONE}"
}

set_txt() {
  local domain="$1"
  local token="$2"
  local record_name
  record_name="$(record_name_for_domain "$domain")"
  python3 "$HELPER" txt-set \
    --zone "$FREEDNS42_ZONE" \
    --record-name "$record_name" \
    --text "$token" \
    --write
}

delete_txt() {
  local domain="$1"
  local token="$2"
  local record_name
  record_name="$(record_name_for_domain "$domain")"
  python3 "$HELPER" txt-delete \
    --zone "$FREEDNS42_ZONE" \
    --record-name "$record_name" \
    --text "$token" \
    --write
}

wait_propagation() {
  local fqdn="$1"
  local token="$2"
  local timeout="$3"
  local interval="$4"
  local server="$5"
  local start
  start="$(date +%s)"

  echo "waiting for TXT ${fqdn} on ${server}, timeout ${timeout}s" >&2

  while true; do
    local now elapsed answer
    now="$(date +%s)"
    elapsed=$((now-start))
    answer="$(dig +short @"$server" TXT "$fqdn" 2>/dev/null | tr -d '\"' | paste -sd ',' -)"

    if echo "$answer" | grep -Fq "$token"; then
      echo "TXT visible after ${elapsed}s: ${answer}" >&2
      return 0
    fi

    if (( elapsed >= timeout )); then
      echo "TXT not visible after ${elapsed}s on ${server}: ${answer:-<empty>}" >&2
      return 1
    fi

    sleep "$interval"
  done
}

wait_recursive_visibility() {
  local fqdn="$1"
  local token="$2"
  local timeout="$3"
  local interval="$4"
  shift 4
  local servers=("$@")
  local start
  start="$(date +%s)"

  if [[ "${#servers[@]}" -eq 0 ]]; then
    return 0
  fi

  echo "waiting for recursive DNS visibility of TXT ${fqdn} on ${servers[*]}, timeout ${timeout}s" >&2

  while true; do
    local now elapsed pending=()
    now="$(date +%s)"
    elapsed=$((now-start))

    for server in "${servers[@]}"; do
      local answer
      answer="$(dig +short @"$server" TXT "$fqdn" 2>/dev/null | tr -d '\"' | paste -sd ',' -)"
      if ! echo "$answer" | grep -Fq "$token"; then
        pending+=("${server}:${answer:-<empty>}")
      fi
    done

    if [[ "${#pending[@]}" -eq 0 ]]; then
      echo "TXT visible on recursive resolvers after ${elapsed}s" >&2
      return 0
    fi

    if (( elapsed >= timeout )); then
      echo "TXT not visible on all recursive resolvers after ${elapsed}s: ${pending[*]}" >&2
      return 1
    fi

    sleep "$interval"
  done
}

usage() {
  cat <<'EOF'
Usage:
  freedns42_acme_hook.sh present <domain> <validation>
  freedns42_acme_hook.sh cleanup <domain> <validation>

Required env:
  FREEDNS42_USER
  FREEDNS42_PASSWORD

  Optional env:
  FREEDNS42_ZONE=efork.pl
  FREEDNS42_PROPAGATION_SECONDS=900
  FREEDNS42_PROPAGATION_INTERVAL_SECONDS=15
  FREEDNS42_DNS_SERVER=fns1.42.pl
  FREEDNS42_RECURSIVE_TIMEOUT_SECONDS=300
  FREEDNS42_RECURSIVE_DNS_SERVERS="1.1.1.1 8.8.8.8"

Examples:
  FREEDNS42_USER=fork FREEDNS42_PASSWORD=... ./tools/freedns42_acme_hook.sh present '*.efork.pl' token
  FREEDNS42_USER=fork FREEDNS42_PASSWORD=... ./tools/freedns42_acme_hook.sh cleanup '*.efork.pl' token
EOF
}

main() {
  local action="${1:-}"
  local domain="${2:-}"
  local validation="${3:-}"

  if [[ -z "${FREEDNS42_USER:-}" || -z "${FREEDNS42_PASSWORD:-}" ]]; then
    echo "missing FREEDNS42_USER or FREEDNS42_PASSWORD" >&2
    exit 1
  fi

  case "$action" in
    present)
      [[ -n "$domain" && -n "$validation" ]] || { usage >&2; exit 1; }
      set_txt "$domain" "$validation"
      wait_propagation \
        "$(record_fqdn_for_domain "$domain")" \
        "$validation" \
        "$FREEDNS42_PROPAGATION_SECONDS" \
        "$FREEDNS42_PROPAGATION_INTERVAL_SECONDS" \
        "$FREEDNS42_DNS_SERVER"
      IFS=' ' read -r -a recursive_servers <<< "$FREEDNS42_RECURSIVE_DNS_SERVERS"
      wait_recursive_visibility \
        "$(record_fqdn_for_domain "$domain")" \
        "$validation" \
        "$FREEDNS42_RECURSIVE_TIMEOUT_SECONDS" \
        "$FREEDNS42_PROPAGATION_INTERVAL_SECONDS" \
        "${recursive_servers[@]}"
      ;;
    cleanup)
      [[ -n "$domain" && -n "$validation" ]] || { usage >&2; exit 1; }
      delete_txt "$domain" "$validation"
      ;;
    *)
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
