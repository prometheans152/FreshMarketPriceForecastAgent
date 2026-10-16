#!/usr/bin/env bash
# Applies a narrowly scoped, authenticated Oracle website to the existing
# verified ForecastEngine. Does NOT replace/retrain any model, Oracle origin
# bearer secret, Windows web/records, or unrelated Nginx sites/services.
set -euo pipefail
umask 077

if [ "$#" -ne 2 ] || [ "$(id -u)" -ne 0 ]; then
    echo "Usage: sudo bash install_web_overlay.sh TRUSTED_STAGE RELEASE_TAG" >&2
    exit 2
fi
STAGE="$1"
TAG="$2"
case "$STAGE" in /home/ubuntu/tw01-web-stage-*) ;; *) echo "invalid stage path" >&2; exit 2;; esac
if [[ ! "$TAG" =~ ^[a-zA-Z0-9_-]+$ ]]; then exit 2; fi

SITE_ROOT=/var/www/tw01-website
OVERLAY_ROOT=/opt/tw01-forecastengine-web
CONF=/etc/nginx/sites-available/tw01-tls.conf
ACME_CONF=/etc/nginx/sites-available/tw01-acme.conf
BACKUP_TLS="$CONF.pre-web-$TAG"
BACKUP_HTTP="$ACME_CONF.pre-web-$TAG"
HTPASSWD=/etc/nginx/.tw01-web.htpasswd
LOGIN_FILE=/etc/tw01-forecastengine/web-login.txt
SNIPPET=/etc/nginx/snippets/tw01-web-auth.conf
OVERRIDE=/etc/systemd/system/tw01-forecastengine.service.d/20-web-frontend.conf
installed_override=0
backup_complete=0

rollback() {
    rc="$?"
    if [ "$rc" -ne 0 ]; then
        echo "WEB_OVERLAY_FAILED=$rc; attempting a scoped rollback" >&2
        if [ "$backup_complete" = 1 ]; then
            cp -p "$BACKUP_TLS" "$CONF" || true
            cp -p "$BACKUP_HTTP" "$ACME_CONF" || true
        fi
        if [ "$installed_override" = 1 ]; then
            rm -f "$OVERRIDE"
            systemctl daemon-reload || true
            systemctl restart tw01-forecastengine.service || true
        fi
        nginx -t && systemctl reload nginx.service || true
    fi
    exit "$rc"
}
trap rollback EXIT

for item in \
    "$STAGE/oracle_web_site.py" "$STAGE/nginx-web-snippet.conf" \
    "$STAGE/tw01-web-service-override.conf" "$STAGE/nginx-acme.conf" \
    "$STAGE/site/index.html" "$STAGE/site/app.js" "$STAGE/site/style.css"; do
    test -f "$item" && test ! -L "$item"
done
for item in \
    "$SITE_ROOT" "$OVERLAY_ROOT" "$SNIPPET" "$LOGIN_FILE" "$HTPASSWD" \
    "$OVERRIDE" "$BACKUP_TLS" "$BACKUP_HTTP"; do
    if [ -e "$item" ] || [ -L "$item" ]; then
        echo "REFUSE_OVERWRITE=$item" >&2
        exit 2
    fi
done
test -f "$CONF" && test -f "$ACME_CONF"
test "$(systemctl is-active tw01-forecastengine.service)" = active
test "$(systemctl is-active nginx.service)" = active
test "$(stat -c %a /etc/tw01-forecastengine/origin.env)" = 600
test "$(readlink /etc/nginx/sites-enabled/tw01-tls.conf)" = "$CONF"
test -d /opt/tw01-forecastengine/current/models/releases/0.1.0
getent group www-data >/dev/null

install -d -m 0755 -o root -g root "$SITE_ROOT" "$OVERLAY_ROOT" "$OVERLAY_ROOT/site_overlay"
for asset in index.html app.js style.css; do
    install -m 0644 -o root -g root "$STAGE/site/$asset" "$SITE_ROOT/$asset"
done
install -m 0644 -o root -g root "$STAGE/oracle_web_site.py" "$OVERLAY_ROOT/site_overlay/oracle_web_site.py"

install -d -m 0755 -o root -g root /etc/nginx/snippets
python3 - <<'PY'
import grp,os,secrets,subprocess
from pathlib import Path
login_file=Path("/etc/tw01-forecastengine/web-login.txt")
hash_file=Path("/etc/nginx/.tw01-web.htpasswd")
password=secrets.token_urlsafe(26)
username="tw01web"
digest=subprocess.run(["openssl","passwd","-apr1","-stdin"],
    input=password+"\n",text=True,check=True,capture_output=True).stdout.strip()
def exclusive(path,contents,mode):
    fd=os.open(str(path),os.O_CREAT|os.O_EXCL|os.O_WRONLY,mode)
    with os.fdopen(fd,"w",encoding="utf-8") as out:
        out.write(contents)
exclusive(login_file,"Username: "+username+"\nPassword: "+password+"\n",0o600)
exclusive(hash_file,username+":"+digest+"\n",0o640)
os.chown(hash_file,0,grp.getgrnam("www-data").gr_gid)
# The installer uses umask 077. os.open(..., 0640) becomes 0600 unless
# explicitly widened AFTER writing; the unprivileged Nginx worker needs read.
os.chmod(hash_file,0o640)
print("SEPARATE_WEB_LOGIN_GENERATED=YES;VALUE_NOT_PRINTED")
PY
printf 'auth_basic "TW01 Private Forecast Web";\nauth_basic_user_file /etc/nginx/.tw01-web.htpasswd;\n' > "$SNIPPET"
chmod 0644 "$SNIPPET"
chown root:root "$SNIPPET"

# Check syntax against the exact live service before introducing drop-ins.
cp -p "$CONF" "$BACKUP_TLS"
cp -p "$ACME_CONF" "$BACKUP_HTTP"
backup_complete=1
python3 - "$STAGE" "$CONF" <<'PY'
from pathlib import Path
import sys
stage=Path(sys.argv[1])
current=Path(sys.argv[2])
source=current.read_text(encoding="utf-8")
marker="    location / { return 404; }\n"
assert source.count(marker)==1,"unexpected origin Nginx config"
snippet=(stage/"nginx-web-snippet.conf").read_text(encoding="utf-8")
current.write_text(source.replace(marker,snippet+"\n"+marker),encoding="utf-8")
print("HTTPS_NGINX_ROUTES_STAGED=YES")
PY
install -m 0644 -o root -g root "$STAGE/nginx-acme.conf" "$ACME_CONF"
nginx -t

install -d -m 0755 -o root -g root /etc/systemd/system/tw01-forecastengine.service.d
install -m 0644 -o root -g root "$STAGE/tw01-web-service-override.conf" "$OVERRIDE"
installed_override=1
systemctl daemon-reload
systemctl restart tw01-forecastengine.service
systemctl is-active --quiet tw01-forecastengine.service

# Keep the original Origin API protected and healthy before Nginx reload.
curl --fail --silent --show-error --max-time 25 http://127.0.0.1:8767/healthz >/dev/null
test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
    -X POST -H 'Content-Type: application/json' \
    --data '{"crop_id":"cabbage","market_id":"中義市場"}' \
    http://127.0.0.1:8767/v1/market-quote)" = 401
systemctl reload nginx.service
curl --fail --silent --show-error --max-time 20 https://161.33.19.220/healthz >/dev/null
echo "WEB_OVERLAY_INSTALLED=YES"
systemctl show tw01-forecastengine.service -p ActiveState -p MainPID -p MemoryCurrent --no-pager
