#!/usr/bin/env bash
set -euo pipefail

SSH_KEY="${SSH_KEY:-/root/.ssh/id_mikrotik}"
ROUTERS=(
  192.168.1.2
  192.168.1.3
  192.168.1.4
  192.168.1.5
  192.168.1.6
  192.168.1.7
  192.168.1.8
  192.168.1.9
)

for ip in "${ROUTERS[@]}"; do
  echo "=== $ip ==="
  ssh -o BatchMode=yes -o StrictHostKeyChecking=no -i "$SSH_KEY" "admin@$ip" \
    '/system logging action print detail; /system logging print detail where action=remote'
  echo
done
