#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


HTML = """<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MikroTik Logs</title>
  <style>
    :root {
      --bg: #0f172a;
      --panel: #111827;
      --panel-2: #1f2937;
      --text: #e5e7eb;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --danger: #f87171;
      --border: #334155;
    }
    body {
      margin: 0;
      font-family: system-ui, sans-serif;
      background: linear-gradient(180deg, #0b1220 0%%, var(--bg) 100%%);
      color: var(--text);
    }
    .wrap {
      max-width: 1280px;
      margin: 0 auto;
      padding: 24px;
    }
    h1 {
      margin: 0 0 18px;
      font-size: 32px;
    }
    .toolbar {
      display: grid;
      grid-template-columns: 220px 1fr 160px 140px 140px;
      gap: 12px;
      background: rgba(17, 24, 39, 0.92);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 16px;
      position: sticky;
      top: 16px;
      backdrop-filter: blur(8px);
      margin-bottom: 18px;
    }
    label {
      display: block;
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 6px;
    }
    input, select, button {
      width: 100%%;
      box-sizing: border-box;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: var(--panel-2);
      color: var(--text);
      padding: 12px 14px;
      font-size: 15px;
    }
    button {
      background: var(--accent);
      color: #082f49;
      font-weight: 700;
      cursor: pointer;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .card {
      background: rgba(17, 24, 39, 0.92);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 16px;
    }
    .card .k {
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }
    .card .v {
      font-size: 28px;
      font-weight: 800;
    }
    table {
      width: 100%%;
      border-collapse: collapse;
      background: rgba(17, 24, 39, 0.92);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
    }
    th, td {
      padding: 12px 14px;
      border-bottom: 1px solid rgba(51, 65, 85, 0.7);
      vertical-align: top;
      text-align: left;
      font-size: 14px;
    }
    th {
      color: var(--muted);
      font-weight: 600;
      background: rgba(31, 41, 55, 0.75);
    }
    tr.error td {
      background: rgba(127, 29, 29, 0.18);
    }
    .msg {
      white-space: pre-wrap;
      word-break: break-word;
    }
    .muted {
      color: var(--muted);
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>MikroTik Logs</h1>
    <div class="toolbar">
      <div>
        <label for="source">Router IP</label>
        <select id="source"></select>
      </div>
      <div>
        <label for="q">Szukaj</label>
        <input id="q" placeholder="error, failed, login, wireguard...">
      </div>
      <div>
        <label for="errorsOnly">Widok</label>
        <select id="errorsOnly">
          <option value="1">Tylko błędy</option>
          <option value="0">Wszystko</option>
        </select>
      </div>
      <div>
        <label for="limit">Limit</label>
        <select id="limit">
          <option>50</option>
          <option selected>100</option>
          <option>200</option>
          <option>500</option>
        </select>
      </div>
      <div style="align-self:end">
        <button id="reload">Odśwież</button>
      </div>
    </div>

    <div class="stats">
      <div class="card"><div class="k">Wszystkie</div><div class="v" id="allCount">-</div></div>
      <div class="card"><div class="k">Błędy</div><div class="v" id="errCount">-</div></div>
      <div class="card"><div class="k">Routery</div><div class="v" id="routerCount">-</div></div>
      <div class="card"><div class="k">Ostatni wpis</div><div class="v" id="lastSeen" style="font-size:18px">-</div></div>
    </div>

    <table>
      <thead>
        <tr>
          <th style="width: 190px;">Czas</th>
          <th style="width: 120px;">Router</th>
          <th style="width: 70px;">Lvl</th>
          <th>Wiadomość</th>
        </tr>
      </thead>
      <tbody id="rows"></tbody>
    </table>
  </div>

  <script>
    const source = document.getElementById('source');
    const q = document.getElementById('q');
    const errorsOnly = document.getElementById('errorsOnly');
    const limit = document.getElementById('limit');
    const rows = document.getElementById('rows');
    const allCount = document.getElementById('allCount');
    const errCount = document.getElementById('errCount');
    const routerCount = document.getElementById('routerCount');
    const lastSeen = document.getElementById('lastSeen');
    document.getElementById('reload').addEventListener('click', loadData);

    function esc(v) {
      return String(v ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    }

    async function loadSources() {
      const r = await fetch('/api/routers');
      const data = await r.json();
      source.innerHTML = '<option value="">Wszystkie</option>' + data.routers.map(ip => `<option value="${esc(ip)}">${esc(ip)}</option>`).join('');
    }

    async function loadSummary() {
      const r = await fetch('/api/summary');
      const data = await r.json();
      allCount.textContent = data.total_logs;
      errCount.textContent = data.error_logs;
      routerCount.textContent = data.router_count;
      lastSeen.textContent = data.last_seen || '-';
    }

    async function loadData() {
      const params = new URLSearchParams({
        source_ip: source.value,
        q: q.value,
        errors_only: errorsOnly.value,
        limit: limit.value
      });
      const r = await fetch('/api/logs?' + params.toString());
      const data = await r.json();
      rows.innerHTML = data.logs.map(item => `
        <tr class="${item.is_error ? 'error' : ''}">
          <td>${esc(item.received_at)}</td>
          <td>${esc(item.source_ip)}</td>
          <td>${esc(item.severity_label || '')}</td>
          <td class="msg">${esc(item.message)}</td>
        </tr>
      `).join('') || '<tr><td colspan="4" class="muted">Brak wyników</td></tr>';
    }

    async function boot() {
      await loadSources();
      await loadSummary();
      await loadData();
    }

    q.addEventListener('keydown', (e) => { if (e.key === 'Enter') loadData(); });
    source.addEventListener('change', loadData);
    errorsOnly.addEventListener('change', loadData);
    limit.addEventListener('change', loadData);
    boot();
  </script>
</body>
</html>
"""

SEVERITY_LABELS = {
    0: "emerg",
    1: "alert",
    2: "crit",
    3: "err",
    4: "warn",
    5: "notice",
    6: "info",
    7: "debug",
}


def is_error_row(severity: int | None, message: str) -> bool:
    if severity is not None and severity <= 4:
        return True
    lower = message.lower()
    return any(token in lower for token in ("error", "failed", "failure", "critical", "denied", "invalid"))


def open_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


class App:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def routers(self) -> dict:
        with open_db(self.db_path) as conn:
            rows = conn.execute("SELECT DISTINCT source_ip FROM logs ORDER BY source_ip").fetchall()
        return {"routers": [row["source_ip"] for row in rows]}

    def summary(self) -> dict:
        with open_db(self.db_path) as conn:
            total_logs = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
            router_count = conn.execute("SELECT COUNT(DISTINCT source_ip) FROM logs").fetchone()[0]
            last_seen = conn.execute("SELECT received_at FROM logs ORDER BY id DESC LIMIT 1").fetchone()
            error_rows = conn.execute(
                """
                SELECT COUNT(*) FROM logs
                WHERE severity <= 4
                   OR lower(message) LIKE '%error%'
                   OR lower(message) LIKE '%failed%'
                   OR lower(message) LIKE '%failure%'
                   OR lower(message) LIKE '%critical%'
                   OR lower(message) LIKE '%denied%'
                   OR lower(message) LIKE '%invalid%'
                """
            ).fetchone()[0]
        return {
            "total_logs": total_logs,
            "error_logs": error_rows,
            "router_count": router_count,
            "last_seen": last_seen[0] if last_seen else None,
        }

    def logs(self, source_ip: str, query: str, errors_only: bool, limit: int) -> dict:
        sql = "SELECT id, received_at, source_ip, severity, message FROM logs WHERE 1=1"
        params: list = []
        if source_ip:
            sql += " AND source_ip = ?"
            params.append(source_ip)
        if query:
            sql += " AND lower(message) LIKE ?"
            params.append(f"%{query.lower()}%")
        if errors_only:
            sql += """
                AND (
                    severity <= 4
                    OR lower(message) LIKE '%error%'
                    OR lower(message) LIKE '%failed%'
                    OR lower(message) LIKE '%failure%'
                    OR lower(message) LIKE '%critical%'
                    OR lower(message) LIKE '%denied%'
                    OR lower(message) LIKE '%invalid%'
                )
            """
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with open_db(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()

        payload = []
        for row in rows:
            severity = row["severity"]
            message = row["message"]
            payload.append(
                {
                    "id": row["id"],
                    "received_at": row["received_at"],
                    "source_ip": row["source_ip"],
                    "severity": severity,
                    "severity_label": SEVERITY_LABELS.get(severity),
                    "message": message,
                    "is_error": is_error_row(severity, message),
                }
            )
        return {"logs": payload}


class Handler(BaseHTTPRequestHandler):
    app: App

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/":
            self._send_html(HTML)
            return
        if parsed.path == "/health":
            self._send_json({"status": "ok"})
            return
        if parsed.path == "/api/routers":
            self._send_json(self.app.routers())
            return
        if parsed.path == "/api/summary":
            self._send_json(self.app.summary())
            return
        if parsed.path == "/api/logs":
            source_ip = qs.get("source_ip", [""])[0].strip()
            query = qs.get("q", [""])[0].strip()
            errors_only = qs.get("errors_only", ["1"])[0] == "1"
            try:
                limit = max(1, min(1000, int(qs.get("limit", ["100"])[0])))
            except ValueError:
                limit = 100
            self._send_json(self.app.logs(source_ip, query, errors_only, limit))
            return
        self._send_json({"detail": f"Not found: {escape(parsed.path)}"}, status=404)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal web UI for MikroTik logs")
    parser.add_argument("--bind", default=os.getenv("MIKROTIK_LOGS_WEB_BIND", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MIKROTIK_LOGS_WEB_PORT", "8514")))
    parser.add_argument(
        "--db-path",
        default=os.getenv("MIKROTIK_LOGS_DB", "/root/mikrotik-logs/data/logs.db"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    Handler.app = App(Path(args.db_path))
    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
