# Central Logging

## Design
All MikroTik routers forward operational logs to the central collector on `192.168.1.15:514/udp`.

Collector:
- Host: `192.168.1.15`
- Service: `mikrotik-logs.service`
- App: `/root/mikrotik-logs/app.py`
- Storage: `/root/mikrotik-logs/data/logs.db`

Router standard:
- Action: built-in `remote`
- Target: `192.168.1.15`
- Port: `514`
- Protocol: `udp`
- Format: `default`

Forwarded topics:
- `info,!container`
- `warning`
- `error`
- `critical`

This keeps infrastructure and security events centralized while avoiding high-volume container debug spam from RouterOS container hosts.

## Current Scope
Managed routers:
- `192.168.1.2` `L009_Glowny`
- `192.168.1.3` `ufo_Salon`
- `192.168.1.4` `ax2_Leon`
- `192.168.1.5` `ufo_Hall`
- `192.168.1.6` `Zewnetrzny`
- `192.168.1.7` `ax3_Kotlownia`
- `192.168.1.8` `ax3_Marek`
- `192.168.1.9` `SXT_Sauna`

## Operations
Audit router logging:
```bash
./tools/mikrotik_syslog_audit.sh
```

Re-apply the standard:
```bash
./tools/mikrotik_syslog_apply.sh
```

Check collector health:
```bash
ssh -i /root/.ssh/id_mikrotik root@192.168.1.15 'systemctl status mikrotik-logs.service'
ssh -i /root/.ssh/id_mikrotik root@192.168.1.15 'ss -lunp | grep ":514 "'
```

## Notes
- `ax3_Kotlownia` previously flooded the collector with `container,info,debug` logs. The standard excludes `container` from the `info` rule.
- If container logs are needed centrally in the future, route them to a separate collector or store them with a dedicated filter and retention policy.
