#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import socket
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at TEXT NOT NULL,
    source_ip TEXT NOT NULL,
    source_port INTEGER NOT NULL,
    facility INTEGER,
    severity INTEGER,
    message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_logs_received_at ON logs(received_at);
CREATE INDEX IF NOT EXISTS idx_logs_source_ip ON logs(source_ip);
"""


def parse_syslog_payload(payload: bytes) -> tuple[int | None, int | None, str]:
    text = payload.decode("utf-8", errors="replace").strip()
    facility = None
    severity = None
    if text.startswith("<"):
        end = text.find(">")
        if end > 1:
            pri_text = text[1:end]
            if pri_text.isdigit():
                pri = int(pri_text)
                facility = pri // 8
                severity = pri % 8
                text = text[end + 1 :].lstrip()
    return facility, severity, text


def ensure_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def serve(bind: str, port: int, db_path: Path) -> int:
    conn = ensure_db(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.commit()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((bind, port))

    running = True

    def stop_handler(signum, frame):  # noqa: ARG001
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    while running:
        try:
            payload, (src_ip, src_port) = sock.recvfrom(65535)
        except OSError:
            break
        facility, severity, message = parse_syslog_payload(payload)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO logs(received_at, source_ip, source_port, facility, severity, message) VALUES (?, ?, ?, ?, ?, ?)",
            (now, src_ip, src_port, facility, severity, message),
        )
        conn.commit()

    sock.close()
    conn.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal MikroTik UDP syslog collector")
    parser.add_argument("--bind", default=os.getenv("MIKROTIK_LOGS_BIND", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MIKROTIK_LOGS_PORT", "514")))
    parser.add_argument(
        "--db-path",
        default=os.getenv("MIKROTIK_LOGS_DB", "/root/mikrotik-logs/data/logs.db"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return serve(args.bind, args.port, Path(args.db_path))
    except PermissionError as exc:
        print(f"Permission error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
