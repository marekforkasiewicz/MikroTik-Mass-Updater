#!/usr/bin/env bash
set -euo pipefail

SSH_KEY="${SSH_KEY:-/root/.ssh/id_mikrotik}"
COLLECTOR_IP="${COLLECTOR_IP:-192.168.1.14}"
COLLECTOR_PORT="${COLLECTOR_PORT:-514}"
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
  ssh -o BatchMode=yes -o StrictHostKeyChecking=no -i "$SSH_KEY" "admin@$ip" "
:foreach i in=[/system logging find where action=remote] do={/system logging remove \$i};
/system logging action set remote remote=$COLLECTOR_IP remote-port=$COLLECTOR_PORT remote-protocol=udp remote-log-format=default src-address=0.0.0.0 vrf=main;
/system logging add topics=info,!container action=remote;
/system logging add topics=warning action=remote;
/system logging add topics=error action=remote;
/system logging add topics=critical action=remote;
/system logging print detail where action=remote
"
  echo
done
