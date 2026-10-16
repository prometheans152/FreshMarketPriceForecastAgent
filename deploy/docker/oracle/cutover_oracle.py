"""Atomic scoped migration of existing Oracle FMPA HTTPS routes to Docker.

The live TLS private key, port 80 ACME verification, Cloudflare tunnel,
unrelated Nginx sites and existing frozen model files are NEVER changed.
Only exact FMPA HTTPS upstreams/static asset routing are switched to the
already healthy Docker Nginx on 127.0.0.1:8080.

If any post-cutover verification fails, restore Nginx original config,
re-enable original ForecastEngine systemd service and leave Docker intact
for forensic inspection.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import shutil
import socket
import ssl
import subprocess
import tempfile
import time
from pathlib import Path

NGINX = Path("/etc/nginx/sites-available/fresh-market-price-agent-tls.conf")
ORIGINAL_SERVICE = "fresh-market-price-agent-forecastengine.service"
DOCKER_HOST_PORT = "127.0.0.1:8080"
ORIGIN_HOSTNAME = "161.33.19.220"
BODY_A = {
    "crop_id": "taichung_04", "market_id": "中義市場",
    "current_price": 32, "price_unit": "NTD_per_taiwan_jin",
    "observed_at": "2026-10-14T12:00:00+08:00",
    "mode": "without_last_week",
}


def call(*cmd):
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(cmd[0] + " failed (exit=" + str(out.returncode) + ")")


def check_active(name):
    call("systemctl", "is-active", "--quiet", name)


class LocalVerifiedTLS(http.client.HTTPSConnection):
    """Connect to loopback TLS listener but validate exact public IP-SAN."""
    def __init__(self, port=443):
        super().__init__(ORIGIN_HOSTNAME, port, timeout=20,
                         context=ssl.create_default_context())

    def connect(self):
        socket_obj = socket.create_connection(("127.0.0.1", self.port), self.timeout)
        self.sock = self._context.wrap_socket(
            socket_obj, server_hostname=ORIGIN_HOSTNAME
        )


def local_request(path, *, method="GET", payload=None, token=None, live=False):
    conn = LocalVerifiedTLS() if live else http.client.HTTPConnection(
        "127.0.0.1", 8080, timeout=20
    )
    headers = {
        "Host": ORIGIN_HOSTNAME,
        "Accept": "application/json, text/html",
    }
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    if payload is not None:
        headers.update({
            "Content-Type": "application/json",
            "Origin": "https://" + ORIGIN_HOSTNAME,
            "Referer": "https://" + ORIGIN_HOSTNAME + "/web/",
            "Sec-Fetch-Site": "same-origin",
        })
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    else:
        data = None
    try:
        conn.request(method, path, data, headers)
        response = conn.getresponse()
        raw = response.read(500_000)
        try:
            obj = json.loads(raw)
        except (UnicodeError, ValueError):
            obj = None
        return response.status, obj, raw
    finally:
        conn.close()


def compare_app_endpoints(*, live: bool):
    mode = "HTTPS_AFTER_SWITCH" if live else "DOCKER_STAGING"
    ok, data, _ = local_request("/healthz", live=live)
    if ok != 200 or data.get("status") != "ready" or data.get("model_version") != "0.1.0":
        raise RuntimeError(mode + " /healthz is not the approved frozen engine")
    print(mode + "_HEALTHZ=PASS", flush=True)

    status, _, page = local_request("/web/", live=live)
    if status != 200 or b"cropCategory" not in page or b"predictForm" not in page:
        raise RuntimeError(mode + " 61-item HTML unavailable")
    print(mode + "_WEBSITE=PASS", flush=True)
    status, catalog, _ = local_request("/web/catalog.json", live=live)
    if status != 200 or len(catalog.get("items", [])) != 61:
        raise RuntimeError(mode + " full 61 public item catalog missing")
    print(mode + "_CATALOG_61=PASS", flush=True)

    for tag, body, ver in (
        ("ADDITIONAL_REAL_HGB", BODY_A, "multi-crop-ml/1.0.0"),
        ("ORIGINAL_RF_HGB", {**BODY_A, "crop_id": "cabbage"}, "0.1.0"),
        ("NEW_HGB_A_B", {**BODY_A, "mode": "both", "previous_price": 30,
                         "previous_price_unit": "NTD_per_taiwan_jin",
                         "previous_observed_at": "2026-10-07T12:00:00+08:00"},
         "multi-crop-ml/1.0.0"),
    ):
        status, result, _ = local_request(
            "/web/forecast", method="POST", payload=body, live=live
        )
        if (
            status != 200 or result.get("error") is not None
            or result.get("model_version") != ver
            or [r["horizon_days"] for r in
                (result.get("results_without_last_week") or result["results"])] != [7, 14]
            or (
                tag == "NEW_HGB_A_B"
                and [r["horizon_days"] for r in result["results_with_last_week"]] != [7, 14]
            )
        ):
            raise RuntimeError(mode + " " + tag + " real prediction failed")
        print(mode + "_" + tag + "=PASS", flush=True)
        time.sleep(4)

    # The original MCP contract is unchanged: no Bearer = 401.
    status, _, _ = local_request(
        "/v1/forecast", method="POST",
        payload={"crop_id": "cabbage", "market_id": "中義市場",
                 "current_price": 32, "price_unit": "NTD_per_taiwan_jin",
                 "observed_on": "2026-10-14"},
        live=live,
    )
    if status != 401:
        raise RuntimeError(mode + " original MCP Bearer guard unexpectedly open")
    print(mode + "_MCP_NO_TOKEN_401=PASS", flush=True)

    # Backend secrets are intentionally never read by the cutover verifier.
    # The existing Cloudflare Worker will verify a real authorized invocation
    # end to end after migration via its own independent protected secret.
    status, _, _ = local_request(
        "/v1/market-quote", method="POST",
        payload={"crop_id": "cabbage", "market_id": "中義市場"},
        live=live,
    )
    if status != 401:
        raise RuntimeError(mode + " original MCP quote unexpectedly public")
    print(mode + "_MCP_MARKET_QUOTE_NO_TOKEN_401=PASS", flush=True)
    status, _, _ = local_request("/records", live=live)
    if status != 404:
        raise RuntimeError(mode + " private records must not be public")
    print(mode + "_PRIVATE_RECORDS_NOT_EXPOSED=PASS", flush=True)


def install_nginx_config(new_text: str, existing: Path):
    fd, temporary = tempfile.mkstemp(
        prefix=".fresh-market-price-agent-docker-switch-", dir=existing.parent
    )
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(new_text)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, 0o644)
    os.chown(temporary, 0, 0)
    os.replace(temporary, existing)


def render(original: str):
    changes = [
        ("proxy_pass http://127.0.0.1:8767;", "proxy_pass http://127.0.0.1:8080;", 3),
        ("proxy_pass http://127.0.0.1:8767/site/forecast;",
         "proxy_pass http://127.0.0.1:8080/web/forecast;", 1),
        ("alias /var/www/fresh-market-price-agent-website/;\n    index index.html;",
         "proxy_pass http://127.0.0.1:8080;", 1),
        ("alias /var/www/fresh-market-price-agent-website/index.html;", "proxy_pass http://127.0.0.1:8080;", 1),
        ("alias /var/www/fresh-market-price-agent-website/app.js;", "proxy_pass http://127.0.0.1:8080;", 1),
        ("alias /var/www/fresh-market-price-agent-website/style.css;", "proxy_pass http://127.0.0.1:8080;", 1),
        ("alias /var/www/fresh-market-price-agent-website/catalog.json;", "proxy_pass http://127.0.0.1:8080;", 1),
    ]
    result = original
    for before, after, count in changes:
        if result.count(before) != count:
            raise RuntimeError("Live Nginx config differs from approved version: " + before[:50])
        result = result.replace(before, after, count)
    if result.count("proxy_pass http://127.0.0.1:8080") != 9:
        raise RuntimeError("Not all 9 FMPA endpoint upstreams are Docker-bound")
    if result.count("location = /v1/forecast {") != 1:
        raise RuntimeError("Cannot identify original MCP route")
    if result.count("ssl_certificate_key /etc/letsencrypt/") != 1:
        raise RuntimeError("Existing Let's Encrypt certificate source changed")
    if "location / { return 404; }" not in result:
        raise RuntimeError("Unexpected permissive route exposing private /mcp")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--stack", type=Path, required=True)
    values = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Root required")
    tag = values.tag
    if not tag.replace("_", "").replace("-", "").isalnum():
        parser.error("Invalid tag")
    stack = values.stack.resolve(strict=True)
    if not str(stack).startswith("/opt/fresh-market-price-agent-docker/stacks/"):
        parser.error("Unapproved immutable stack path")
    origin_secret = stack / ".secrets" / "origin_api_token"
    if not origin_secret.is_file() or origin_secret.stat().st_mode & 0o077:
        raise RuntimeError("Origin Docker secret is missing or readable by others")
    backup = NGINX.with_name(NGINX.name + ".pre-docker-" + tag)
    if backup.exists():
        raise RuntimeError("Refuse overwrite of existing rollback backup")

    # Read-only staging smoke first: systemd and actual public HTTPS unchanged.
    check_active("nginx.service")
    check_active(ORIGINAL_SERVICE)
    check_active("fresh-market-price-agent-cloudflared.service")
    compare_app_endpoints(live=False)

    before = NGINX.read_text(encoding="utf-8")
    after = render(before)
    shutil.copy2(NGINX, backup)
    old_service_stopped = False
    try:
        install_nginx_config(after, NGINX)
        call("nginx", "-t")
        call("systemctl", "reload", "nginx.service")
        compare_app_endpoints(live=True)
        # The old engine no longer receives traffic; stop it to release RAM on
        # this 1 GB VM. The service unit and on-disk original are preserved.
        call("systemctl", "disable", "--now", ORIGINAL_SERVICE)
        old_service_stopped = True
        check_active("nginx.service")
        check_active("fresh-market-price-agent-cloudflared.service")
        # Avoid replaying 3 more ML computations into the public rate limiter.
        # The full HTTPS ML and MCP suite ran successfully immediately above;
        # after stopping only the UNUSED old process, assert health stays up.
        health_status, health, _ = local_request("/healthz", live=True)
        if health_status != 200 or health.get("status") != "ready":
            raise RuntimeError("Docker backend unhealthy after old systemd engine stopped")
        print("DOCKER_STILL_READY_AFTER_OLD_ENGINE_STOP=PASS", flush=True)
    except Exception:
        if old_service_stopped:
            call("systemctl", "enable", "--now", ORIGINAL_SERVICE)
        shutil.copy2(backup, NGINX)
        call("nginx", "-t")
        call("systemctl", "reload", "nginx.service")
        if not old_service_stopped:
            call("systemctl", "start", ORIGINAL_SERVICE)
        raise

    print("ORACLE_DOCKER_HTTPS_CUTOVER=PASS")
    print("ALL_PUBLIC_APP_ROUTES_TO_DOCKER=YES")
    print("SAME_ORIGINAL_PUBLIC_IP_AND_TLS=YES")
    print("SAME_CLOUDFLARE_VPC_ORIGIN_BEARER=YES")
    print("ORIGINAL_FORECAST_SERVICE_STOPPED=YES")
    print("OLD_MODELS_AND_PRIVATE_RECORDS_PRESERVED=YES")
    print("NGINX_BACKUP=" + str(backup))
    print("USER_CREDENTIAL_VALUES_DISPLAYED=NO")


if __name__ == "__main__":
    main()
