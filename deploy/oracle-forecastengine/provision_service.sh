#!/usr/bin/env bash
# Run ONLY on the Oracle VPS as root after separate preflight, hash verification
# and installation of a compatible Python 3.12 venv. Does not modify iptables or
# other application services. No reboot or model training.
set -euo pipefail
umask 077

if [[ $# -ne 2 ]]; then
  echo "usage: sudo bash provision_service.sh /home/ubuntu/.../bundle RELEASE_ID" >&2
  exit 2
fi
SOURCE="$1"
RELEASE_ID="$2"
ROOT=/opt/fresh-market-price-agent-forecastengine
case "$SOURCE" in
  /home/ubuntu/fresh-market-price-agent-forecastengine-stage-*/bundle) ;;
  *) echo "unapproved staging path" >&2; exit 2 ;;
esac
if [[ ! "$RELEASE_ID" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "invalid release id" >&2
  exit 2
fi
if [[ "$(id -u)" != 0 ]]; then
  echo "must be executed as root" >&2
  exit 2
fi
DEST="$ROOT/releases/$RELEASE_ID"
if [[ -e "$DEST" || -L "$ROOT/current" || -e /etc/systemd/system/fresh-market-price-agent-forecastengine.service ]]; then
  echo "existing release/current/unit; do not overwrite existing deployment" >&2
  exit 2
fi
if [[ ! -x "$ROOT/venv/bin/python" ]]; then
  echo "Oracle Python venv is not ready" >&2
  exit 2
fi
if [[ ! -r "$SOURCE/TRANSFER_SHA256.json" ]]; then
  echo "signed-off bundle manifest missing" >&2
  exit 2
fi

python3 - "$SOURCE" <<'PY'
import hashlib, json, pathlib, sys
source=pathlib.Path(sys.argv[1]).resolve(strict=True)
manifest=source/"TRANSFER_SHA256.json"
fixed_manifest_sha="b3cdd0cc9e84e9aa33346e7cc85ad34026abba4a9d4327e104d92576ccff82ff"
assert hashlib.sha256(manifest.read_bytes()).hexdigest()==fixed_manifest_sha, "manifest hash mismatch"
doc=json.loads(manifest.read_text())
assert doc["bundle_type"]=="TW01_FROZEN_ORACLE_A_ONLY"
assert len(doc["files"])==22
for item in doc["files"]:
    p=source/item["path"]
    assert p.resolve().is_relative_to(source)
    assert p.is_file() and not p.is_symlink()
    assert len(p.read_bytes())==item["bytes"]
    assert hashlib.sha256(p.read_bytes()).hexdigest()==item["sha256"], item["path"]
assert not (source/"private").exists()
assert not (source/"web").exists()
print("PRE_INSTALL_SHA256_PASS=22")
PY

install -d -o root -g root -m 0755 "$ROOT" "$ROOT/releases"
cp -a "$SOURCE" "$DEST"
chown -R root:root "$DEST"
chmod -R go-w "$DEST"
find "$DEST" -type d -exec chmod 0755 {} +
find "$DEST" -type f -exec chmod 0644 {} +
python3 - "$DEST" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1])
data=json.loads((root/"TRANSFER_SHA256.json").read_text())
for f in data["files"]:
    assert hashlib.sha256((root/f["path"]).read_bytes()).hexdigest()==f["sha256"],f["path"]
print("INSTALLED_SHA256_PASS=22")
PY

if ! id tw01forecast &>/dev/null; then
  useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin --user-group tw01forecast
fi
install -d -o root -g root -m 0700 /etc/fresh-market-price-agent-forecastengine
if [[ -e /etc/fresh-market-price-agent-forecastengine/origin.env ]]; then
  echo "secret file already exists; refusing to reuse a previous deployment secret" >&2
  exit 2
fi
python3 - <<'PY'
import os,secrets
path="/etc/fresh-market-price-agent-forecastengine/origin.env"
fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,"w",encoding="ascii") as stream:
    stream.write("FMPA_ORIGIN_API_TOKEN="+secrets.token_urlsafe(48)+"\n")
print("DEDICATED_NEW_ORIGIN_SECRET_CREATED=1")  # never output the value
PY
ln -s "$DEST" "$ROOT/current"
install -o root -g root -m 0644 "$SOURCE/../fresh-market-price-agent-forecastengine.service" /etc/systemd/system/fresh-market-price-agent-forecastengine.service
systemctl daemon-reload
systemctl enable --now fresh-market-price-agent-forecastengine.service
systemctl is-active --quiet fresh-market-price-agent-forecastengine.service
sleep 2
curl --fail --silent --show-error --max-time 20 http://127.0.0.1:8767/healthz
printf '\nSERVICE_INSTALLED=1\n'
systemctl show fresh-market-price-agent-forecastengine.service -p ActiveState -p SubState -p MainPID -p Restart -p MemoryMax -p MemoryHigh -p CPUQuotaPerSecUSec --no-pager
ss -lntp | grep -F '127.0.0.1:8767'
