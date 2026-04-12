#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests


class NpmApi:
    def __init__(self, base_url: str, identity: str, secret: str):
        self.base_url = base_url.rstrip("/")
        self.identity = identity
        self.secret = secret
        self.session = requests.Session()
        self.token: str | None = None

    def login(self) -> str:
        response = self.session.post(
            f"{self.base_url}/tokens",
            json={"identity": self.identity, "secret": self.secret},
            timeout=20,
        )
        response.raise_for_status()
        self.token = response.json()["token"]
        return self.token

    def headers(self) -> dict[str, str]:
        if not self.token:
            self.login()
        return {"Authorization": "Bearer " + self.token}

    def certificates(self) -> list[dict]:
        response = self.session.get(f"{self.base_url}/nginx/certificates", headers=self.headers(), timeout=20)
        response.raise_for_status()
        return response.json()

    def find_certificate(self, nice_name: str) -> dict | None:
        for cert in self.certificates():
            if cert.get("nice_name") == nice_name:
                return cert
        return None

    def create_certificate(self, nice_name: str, domains: list[str]) -> dict:
        payload = {
            "provider": "other",
            "nice_name": nice_name,
            "domain_names": domains,
        }
        response = self.session.post(
            f"{self.base_url}/nginx/certificates",
            headers=self.headers(),
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def upload_certificate(self, cert_id: int, cert_path: Path, key_path: Path, chain_path: Path | None) -> dict:
        files = {
            "certificate": (cert_path.name, cert_path.read_bytes(), "application/x-pem-file"),
            "certificate_key": (key_path.name, key_path.read_bytes(), "application/x-pem-file"),
        }
        if chain_path and chain_path.exists():
            files["intermediate_certificate"] = (
                chain_path.name,
                chain_path.read_bytes(),
                "application/x-pem-file",
            )
        response = self.session.post(
            f"{self.base_url}/nginx/certificates/{cert_id}/upload",
            headers=self.headers(),
            files=files,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def get_proxy_host(self, host_id: int) -> dict:
        response = self.session.get(
            f"{self.base_url}/nginx/proxy-hosts/{host_id}",
            headers=self.headers(),
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def update_proxy_host_certificate(self, host_id: int, certificate_id: int) -> dict:
        host = self.get_proxy_host(host_id)
        payload = {
            "domain_names": host["domain_names"],
            "forward_scheme": host["forward_scheme"],
            "forward_host": host["forward_host"],
            "forward_port": host["forward_port"],
            "access_list_id": host["access_list_id"],
            "certificate_id": certificate_id,
            "ssl_forced": host.get("ssl_forced", False),
            "caching_enabled": host["caching_enabled"],
            "block_exploits": host["block_exploits"],
            "advanced_config": host["advanced_config"],
            "meta": host.get("meta", {}),
            "allow_websocket_upgrade": host["allow_websocket_upgrade"],
            "http2_support": host.get("http2_support", False),
            "hsts_enabled": host["hsts_enabled"],
            "hsts_subdomains": host["hsts_subdomains"],
            "enabled": host["enabled"],
            "locations": host["locations"],
            "trust_forwarded_proto": host.get("trust_forwarded_proto", False),
        }
        response = self.session.put(
            f"{self.base_url}/nginx/proxy-hosts/{host_id}",
            headers=self.headers(),
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        return response.json()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import custom certificate into NPM")
    parser.add_argument("--npm-url", default="http://127.0.0.1:81/api")
    parser.add_argument("--identity", required=True)
    parser.add_argument("--secret", required=True)
    parser.add_argument("--nice-name", required=True)
    parser.add_argument("--domains", required=True, help="Comma-separated domains")
    parser.add_argument("--cert", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--chain")
    parser.add_argument("--assign-proxy-host-id", type=int)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    api = NpmApi(args.npm_url, args.identity, args.secret)
    domains = [x.strip() for x in args.domains.split(",") if x.strip()]
    cert = api.find_certificate(args.nice_name)
    if cert is None:
      cert = api.create_certificate(args.nice_name, domains)
    upload = api.upload_certificate(cert["id"], Path(args.cert), Path(args.key), Path(args.chain) if args.chain else None)
    result: dict[str, object] = {"certificate": upload}
    if args.assign_proxy_host_id:
        result["proxy_host"] = api.update_proxy_host_certificate(args.assign_proxy_host_id, cert["id"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
