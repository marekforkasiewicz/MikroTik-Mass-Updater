#!/usr/bin/env python3
"""
Minimal helper for managing FreeDNS::42 zones through the legacy web panel.

It logs in using the standard HTML form, fetches the zone modify form,
exports current records to JSON, computes a plan versus a desired JSON file,
and can apply the diff back to the panel in small POST batches.

The panel is old-school:
- no cookies; it passes `idsession` in URLs and forms
- existing records are deleted using `deleteN` checkboxes
- new records are added via up to 4 empty inputs per section per request

The helper is intentionally conservative:
- default mode is read-only
- writes require `apply --write`
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xmlrpc.client
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://freedns.42.pl"
LOGIN_URL = f"{BASE_URL}/index.php"
XMLRPC_URL = f"{BASE_URL}/xmlrpc.php"

SUPPORTED_RECORD_TYPES = ("ns", "mx", "a", "cname", "txt", "www")


class FreeDNS42Error(RuntimeError):
    pass


@dataclass
class RecordRef:
    record_type: str
    data: dict[str, Any]
    delete_field: str | None = None
    delete_value: str | None = None
    immutable: bool = False


class FreeDNS42Client:
    def __init__(self, user: str, password: str, language: str = "pl", timeout: int = 20):
        self.user = user
        self.password = password
        self.language = language
        self.timeout = timeout
        self.session = requests.Session()
        self.idsession: str | None = None

    def login(self) -> str:
        response = self.session.post(
            LOGIN_URL,
            data={"login": self.user, "password": self.password, "language": self.language},
            timeout=self.timeout,
        )
        response.raise_for_status()
        match = re.search(r"idsession=([0-9a-f]+)", response.text)
        if not match:
            raise FreeDNS42Error("Login failed: session id not found in response")
        self.idsession = match.group(1)
        return self.idsession

    def ensure_login(self) -> str:
        if self.idsession:
            return self.idsession
        return self.login()

    def fetch_modify_page(self, zone: str, zone_type: str = "P") -> str:
        sid = self.ensure_login()
        response = self.session.get(
            f"{BASE_URL}/modify.php",
            params={"idsession": sid, "zonename": zone, "zonetype": zone_type},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.text

    def submit_modify_form(self, payload: dict[str, str]) -> str:
        response = self.session.post(
            f"{BASE_URL}/modify.php",
            data=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.text


def text_cells(row) -> list[str]:
    cells = []
    for cell in row.find_all(["th", "td"], recursive=False):
        cells.append(" ".join(cell.stripped_strings).strip())
    return cells


def normalize_name(value: str) -> str:
    return value.strip()


def normalize_dot_name(value: str) -> str:
    return value.strip()


def normalize_zone_export(data: dict[str, Any]) -> dict[str, Any]:
    result = {
        "zone": data["zone"],
        "zonetype": data.get("zonetype", "P"),
        "records": {},
        "xferip": data.get("xferip", ""),
    }
    for key in SUPPORTED_RECORD_TYPES:
        records = data.get("records", {}).get(key, [])
        result["records"][key] = sorted(records, key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
    return result


def normalize_record_name_for_zone(name: str, zone: str) -> str:
    raw = name.strip().rstrip(".")
    zone_clean = zone.strip().rstrip(".")
    if raw in {"@", ""}:
        return "@"
    wildcard_prefix = "*."
    if raw == zone_clean:
        return "@"
    suffix = f".{zone_clean}"
    if raw.endswith(suffix):
        raw = raw[: -len(suffix)]
    if raw == wildcard_prefix.rstrip(".") + zone_clean:
        return "*"
    return raw


def make_desired_from_live(page: dict[str, Any]) -> dict[str, Any]:
    return normalize_zone_export(page)


def upsert_txt_record(desired: dict[str, Any], record_name: str, text: str) -> dict[str, Any]:
    name = normalize_record_name_for_zone(record_name, desired["zone"])
    records = list(desired["records"].get("txt", []))
    filtered = [rec for rec in records if not (rec.get("name", "") == name and rec.get("text", "") == text)]
    filtered.append({"name": name, "text": text})
    desired["records"]["txt"] = sorted(
        filtered,
        key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False),
    )
    return desired


def delete_txt_record(desired: dict[str, Any], record_name: str, text: str | None) -> dict[str, Any]:
    name = normalize_record_name_for_zone(record_name, desired["zone"])
    records = list(desired["records"].get("txt", []))
    if text is None:
        filtered = [rec for rec in records if rec.get("name", "") != name]
    else:
        filtered = [rec for rec in records if not (rec.get("name", "") == name and rec.get("text", "") == text)]
    desired["records"]["txt"] = sorted(
        filtered,
        key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False),
    )
    return desired


def parse_modify_page(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form", method="POST")
    if not form:
        raise FreeDNS42Error("Modify form not found")

    hidden_fields: dict[str, str] = {}
    for tag in form.find_all("input"):
        name = tag.get("name")
        if not name:
            continue
        if tag.get("type") == "hidden":
            hidden_fields[name] = tag.get("value", "")

    section_records: dict[str, list[RecordRef]] = {key: [] for key in SUPPORTED_RECORD_TYPES}

    headers = form.find_all("h3", class_="boxheader")
    for header in headers:
        title = header.get_text(" ", strip=True)
        tables = []
        node = header
        while True:
            node = node.find_next_sibling()
            if node is None:
                break
            if getattr(node, "name", None) == "h3":
                break
            if getattr(node, "name", None) == "table":
                tables.append(node)

        if title.startswith("Rekordy (NS)"):
            if not tables:
                continue
            table = tables[0]
            for row in table.find_all("tr"):
                cells = text_cells(row)
                checkbox = row.find("input", attrs={"name": re.compile(r"^delete\d+$")})
                if checkbox:
                    host = cells[0] if cells else ""
                    section_records["ns"].append(
                        RecordRef(
                            "ns",
                            {"host": normalize_dot_name(host)},
                            checkbox.get("name"),
                            checkbox.get("value"),
                        )
                    )
                elif len(cells) >= 1 and cells[0] and cells[0] != "Nazwa":
                    section_records["ns"].append(
                        RecordRef("ns", {"host": normalize_dot_name(cells[0])}, immutable=True)
                    )

        elif title.startswith("Rekordy serwerów obsługujących pocztę (MX)"):
            if not tables:
                continue
            table = tables[0]
            for row in table.find_all("tr"):
                cells = text_cells(row)
                checkbox = row.find("input", attrs={"name": re.compile(r"^delete\d+$")})
                if checkbox and len(cells) >= 3:
                    section_records["mx"].append(
                        RecordRef(
                            "mx",
                            {
                                "name": normalize_name(cells[0]),
                                "priority": cells[1].strip(),
                                "host": normalize_dot_name(cells[2]),
                            },
                            checkbox.get("name"),
                            checkbox.get("value"),
                        )
                    )

        elif title.startswith("Rekordy adresów (A)"):
            if len(tables) < 2:
                continue
            ptr_table = tables[0]
            ptr_checkbox = ptr_table.find("input", attrs={"name": "modifyptr"})
            a_table = tables[1]
            for row in a_table.find_all("tr"):
                cells = text_cells(row)
                checkbox = row.find("input", attrs={"name": re.compile(r"^delete\d+$")})
                if checkbox and len(cells) >= 2:
                    section_records["a"].append(
                        RecordRef(
                            "a",
                            {"name": normalize_name(cells[0]), "value": cells[1].strip()},
                            checkbox.get("name"),
                            checkbox.get("value"),
                        )
                    )
            hidden_fields["modifyptr_present"] = "1" if ptr_checkbox else "0"

        elif title.startswith("Rekordy aliasów (CNAME)"):
            if not tables:
                continue
            table = tables[0]
            for row in table.find_all("tr"):
                cells = text_cells(row)
                checkbox = row.find("input", attrs={"name": re.compile(r"^delete\d+$")})
                if checkbox and len(cells) >= 2:
                    section_records["cname"].append(
                        RecordRef(
                            "cname",
                            {"name": normalize_name(cells[0]), "target": normalize_dot_name(cells[1])},
                            checkbox.get("name"),
                            checkbox.get("value"),
                        )
                    )

        elif title.startswith("Rekordy (TXT)"):
            if not tables:
                continue
            table = tables[0]
            for row in table.find_all("tr"):
                cells = text_cells(row)
                checkbox = row.find("input", attrs={"name": re.compile(r"^delete\d+$")})
                if checkbox and len(cells) >= 2:
                    section_records["txt"].append(
                        RecordRef(
                            "txt",
                            {"name": normalize_name(cells[0]), "text": cells[1].strip()},
                            checkbox.get("name"),
                            checkbox.get("value"),
                        )
                    )

        elif title.startswith("Ramki i przekierowania WWW"):
            if not tables:
                continue
            table = tables[0]
            for row in table.find_all("tr"):
                cells = text_cells(row)
                checkbox = row.find("input", attrs={"name": re.compile(r"^delete\d+$")})
                if checkbox and len(cells) >= 3:
                    mode_text = cells[2].lower()
                    if "ramka" in mode_text:
                        mode = "F"
                    elif "czasowe" in mode_text:
                        mode = "R"
                    else:
                        mode = "r"
                    section_records["www"].append(
                        RecordRef(
                            "www",
                            {"name": normalize_name(cells[0]), "target": cells[1].strip(), "mode": mode},
                            checkbox.get("name"),
                            checkbox.get("value"),
                        )
                    )

        elif title.startswith("Komputery, którym wolno transferować całe strefy"):
            if tables:
                xfer = tables[0].find("input", attrs={"name": "xferip"})
                hidden_fields["xferip"] = xfer.get("value", "") if xfer else ""

    parsed = {
        "zone": hidden_fields.get("zonename", ""),
        "zonetype": hidden_fields.get("zonetype", ""),
        "idsession": hidden_fields.get("idsession", ""),
        "form_hidden": hidden_fields,
        "records": {key: [record.data for record in refs] for key, refs in section_records.items()},
        "record_refs": section_records,
        "xferip": hidden_fields.get("xferip", ""),
    }
    return parsed


def record_key(record_type: str, record: dict[str, Any]) -> tuple[Any, ...]:
    if record_type == "a":
        return (record.get("name", ""), record.get("value", ""))
    if record_type == "cname":
        return (record.get("name", ""), record.get("target", ""))
    if record_type == "mx":
        return (record.get("name", ""), str(record.get("priority", "")), record.get("host", ""))
    if record_type == "txt":
        return (record.get("name", ""), record.get("text", ""))
    if record_type == "www":
        return (record.get("name", ""), record.get("target", ""), record.get("mode", ""))
    if record_type == "ns":
        return (record.get("host", ""),)
    raise FreeDNS42Error(f"Unsupported record type: {record_type}")


def build_plan(current: dict[str, Any], desired: dict[str, Any]) -> dict[str, Any]:
    plan: dict[str, Any] = {"zone": current["zone"], "types": {}, "xferip": None}
    for record_type in SUPPORTED_RECORD_TYPES:
        cur_records = current["records"].get(record_type, [])
        des_records = desired.get("records", {}).get(record_type, [])
        cur_map = {record_key(record_type, item): item for item in cur_records}
        des_map = {record_key(record_type, item): item for item in des_records}
        delete_keys = sorted(set(cur_map) - set(des_map))
        add_keys = sorted(set(des_map) - set(cur_map))
        if delete_keys or add_keys:
            plan["types"][record_type] = {
                "delete": [cur_map[key] for key in delete_keys],
                "add": [des_map[key] for key in add_keys],
            }
    current_xfer = current.get("xferip", "") or ""
    desired_xfer = desired.get("xferip", "") or ""
    if current_xfer != desired_xfer:
        plan["xferip"] = {"from": current_xfer, "to": desired_xfer}
    return plan


def has_changes(plan: dict[str, Any]) -> bool:
    return bool(plan["types"]) or plan["xferip"] is not None


def build_post_payload(page: dict[str, Any], plan: dict[str, Any], desired: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    payload = {
        "idsession": page["form_hidden"]["idsession"],
        "zonename": page["form_hidden"]["zonename"],
        "zonetype": page["form_hidden"]["zonetype"],
        "modified": "1",
        "valid": page["form_hidden"].get("valid", "1"),
        "submit": "Utwórz konfigurację strefy",
        "xferip": desired.get("xferip", "") or "",
    }

    # Delete everything that needs to go from the currently visible page.
    delete_count = 0
    visible_deletes = {}
    for record_type, refs in page["record_refs"].items():
        visible_deletes[record_type] = {}
        for ref in refs:
            if ref.delete_field and ref.delete_value:
                visible_deletes[record_type][record_key(record_type, ref.data)] = ref

    for record_type, ops in plan["types"].items():
        for record in ops["delete"]:
            key = record_key(record_type, record)
            ref = visible_deletes.get(record_type, {}).get(key)
            if ref:
                payload[ref.delete_field] = ref.delete_value
                delete_count += 1

    added: dict[str, int] = {}

    def add_records(record_type: str, records: list[dict[str, Any]]):
        nonlocal payload, added
        limit = min(4, len(records))
        added[record_type] = limit
        for idx in range(limit):
            rec = records[idx]
            slot = idx + 1
            if record_type == "a":
                payload[f"aname{slot}"] = rec["name"]
                payload[f"a{slot}"] = rec["value"]
            elif record_type == "cname":
                payload[f"cname{slot}"] = rec["name"]
                payload[f"cnamea{slot}"] = rec["target"]
            elif record_type == "mx":
                payload[f"mxsrc{slot}"] = rec["name"]
                payload[f"mxpref{slot}"] = str(rec["priority"])
                payload[f"mx{slot}"] = rec["host"]
            elif record_type == "txt":
                payload[f"txt{slot}"] = rec["name"]
                payload[f"txtstring{slot}"] = rec["text"]
            elif record_type == "www":
                payload[f"www{slot}"] = rec["name"]
                payload[f"wwwa{slot}"] = rec["target"]
                payload[f"wwwr{slot}"] = rec["mode"]
            elif record_type == "ns":
                payload[f"ns{slot}"] = rec["host"]

    for record_type in SUPPORTED_RECORD_TYPES:
        ops = plan["types"].get(record_type)
        if not ops:
            continue
        add_records(record_type, ops["add"])

    meta = {"delete_count": delete_count, "added": added}
    return payload, meta


def apply_plan(client: FreeDNS42Client, zone: str, zone_type: str, desired: dict[str, Any], write: bool) -> dict[str, Any]:
    iterations: list[dict[str, Any]] = []
    while True:
        page = parse_modify_page(client.fetch_modify_page(zone, zone_type))
        current = normalize_zone_export(page)
        plan = build_plan(current, desired)
        if not has_changes(plan):
            return {"changed": bool(iterations), "iterations": iterations, "final": current}

        payload, meta = build_post_payload(page, plan, desired)
        iteration = {
            "plan": plan,
            "meta": meta,
            "write": write,
        }
        iterations.append(iteration)

        if not write:
            return {"changed": True, "iterations": iterations, "final": current}

        client.submit_modify_form(payload)


def load_desired(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if "records" not in data:
        raise FreeDNS42Error("Desired JSON must contain top-level 'records'")
    return normalize_zone_export(data)


def command_export(args: argparse.Namespace) -> int:
    client = FreeDNS42Client(args.user, args.password, language=args.language)
    page = parse_modify_page(client.fetch_modify_page(args.zone, args.zone_type))
    output = normalize_zone_export(page)
    rendered = json.dumps(output, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(rendered + "\n")
    else:
        print(rendered)
    return 0


def command_plan(args: argparse.Namespace) -> int:
    client = FreeDNS42Client(args.user, args.password, language=args.language)
    page = parse_modify_page(client.fetch_modify_page(args.zone, args.zone_type))
    current = normalize_zone_export(page)
    desired = load_desired(Path(args.file))
    plan = build_plan(current, desired)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


def command_apply(args: argparse.Namespace) -> int:
    client = FreeDNS42Client(args.user, args.password, language=args.language)
    desired = load_desired(Path(args.file))
    result = apply_plan(client, args.zone, args.zone_type, desired, write=args.write)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_dyndns_a(args: argparse.Namespace) -> int:
    params = {
        "user": args.user,
        "password": args.password,
        "zone": args.zone,
        "name": args.record_name,
        "oldaddress": args.old_address,
        "newaddress": args.new_address,
        "ttl": str(args.ttl),
        "updatereverse": "1" if args.update_reverse else "0",
    }
    if not args.write:
        print(json.dumps({"server": args.server, "params": params, "write": False}, ensure_ascii=False, indent=2))
        return 0

    client = xmlrpc.client.ServerProxy(args.server)
    result = client.xname.updateArecord(params)
    print(json.dumps({"server": args.server, "params": params, "result": result, "write": True}, ensure_ascii=False, indent=2))
    return 0


def command_txt_set(args: argparse.Namespace) -> int:
    client = FreeDNS42Client(args.user, args.password, language=args.language)
    page = parse_modify_page(client.fetch_modify_page(args.zone, args.zone_type))
    desired = make_desired_from_live(page)
    desired = upsert_txt_record(desired, args.record_name, args.text)
    result = apply_plan(client, args.zone, args.zone_type, desired, write=args.write)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_txt_delete(args: argparse.Namespace) -> int:
    client = FreeDNS42Client(args.user, args.password, language=args.language)
    page = parse_modify_page(client.fetch_modify_page(args.zone, args.zone_type))
    desired = make_desired_from_live(page)
    desired = delete_txt_record(desired, args.record_name, args.text)
    result = apply_plan(client, args.zone, args.zone_type, desired, write=args.write)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FreeDNS::42 zone helper")
    parser.add_argument("--user", default=os.getenv("FREEDNS42_USER"), help="42.pl login")
    parser.add_argument("--password", default=os.getenv("FREEDNS42_PASSWORD"), help="42.pl password")
    parser.add_argument("--language", default="pl")

    sub = parser.add_subparsers(dest="command", required=True)

    export_cmd = sub.add_parser("export", help="Export zone to JSON")
    export_cmd.add_argument("--zone", required=True)
    export_cmd.add_argument("--zone-type", default="P")
    export_cmd.add_argument("--out")
    export_cmd.set_defaults(func=command_export)

    plan_cmd = sub.add_parser("plan", help="Compare current zone with desired JSON")
    plan_cmd.add_argument("--zone", required=True)
    plan_cmd.add_argument("--zone-type", default="P")
    plan_cmd.add_argument("--file", required=True)
    plan_cmd.set_defaults(func=command_plan)

    apply_cmd = sub.add_parser("apply", help="Apply desired JSON to zone")
    apply_cmd.add_argument("--zone", required=True)
    apply_cmd.add_argument("--zone-type", default="P")
    apply_cmd.add_argument("--file", required=True)
    apply_cmd.add_argument("--write", action="store_true", help="Actually send POST requests")
    apply_cmd.set_defaults(func=command_apply)

    dyndns_cmd = sub.add_parser("dyndns-a", help="Update a single A record through 42.pl XML-RPC")
    dyndns_cmd.add_argument("--zone", required=True)
    dyndns_cmd.add_argument("--record-name", required=True, help="Host label, e.g. @, home, vpn")
    dyndns_cmd.add_argument("--old-address", default="*", help="Previous IPv4 or * wildcard")
    dyndns_cmd.add_argument("--new-address", required=True, help="New IPv4 or <dynamic>")
    dyndns_cmd.add_argument("--ttl", default="600")
    dyndns_cmd.add_argument("--update-reverse", action="store_true")
    dyndns_cmd.add_argument("--server", default=XMLRPC_URL)
    dyndns_cmd.add_argument("--write", action="store_true", help="Actually call XML-RPC updateArecord")
    dyndns_cmd.set_defaults(func=command_dyndns_a)

    txt_set_cmd = sub.add_parser("txt-set", help="Create or ensure TXT record exists")
    txt_set_cmd.add_argument("--zone", required=True)
    txt_set_cmd.add_argument("--zone-type", default="P")
    txt_set_cmd.add_argument("--record-name", required=True, help="Relative or FQDN TXT name")
    txt_set_cmd.add_argument("--text", required=True, help="TXT value")
    txt_set_cmd.add_argument("--write", action="store_true", help="Actually send POST requests")
    txt_set_cmd.set_defaults(func=command_txt_set)

    txt_delete_cmd = sub.add_parser("txt-delete", help="Delete TXT record")
    txt_delete_cmd.add_argument("--zone", required=True)
    txt_delete_cmd.add_argument("--zone-type", default="P")
    txt_delete_cmd.add_argument("--record-name", required=True, help="Relative or FQDN TXT name")
    txt_delete_cmd.add_argument("--text", help="Delete only this exact TXT value; omit to delete all values for the name")
    txt_delete_cmd.add_argument("--write", action="store_true", help="Actually send POST requests")
    txt_delete_cmd.set_defaults(func=command_txt_delete)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.user or not args.password:
        parser.error("Missing credentials. Use --user/--password or env FREEDNS42_USER/FREEDNS42_PASSWORD.")
    try:
        return args.func(args)
    except FreeDNS42Error as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except requests.HTTPError as exc:
        print(f"HTTP ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
