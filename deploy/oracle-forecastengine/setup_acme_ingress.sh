#!/usr/bin/env bash
# First stage of HTTPS: publicly serve ONLY an ACME HTTP-01 challenge on port 80.
# Does not enable the forecast origin over HTTP.
set -euo pipefail
umask 022
STAGE="${1:?stage path required}"
case "$STAGE" in /home/ubuntu/fresh-market-price-agent-forecastengine-stage-*) ;; *) exit 2;; esac
test "$(id -u)" = 0
test -e "$STAGE/nginx-acme.conf"
test -e "$STAGE/fresh-market-price-agent-origin-firewall.sh"

# No pre-existing Nginx apps were found during VPS inventory. Refuse if changed.
for entry in /etc/nginx/sites-enabled/*; do
  [[ ! -e "$entry" && ! -L "$entry" ]] && continue
  if [[ "$entry" != "/etc/nginx/sites-enabled/default" ]]; then
    echo "Unexpected existing Nginx site: $entry; refuse takeover" >&2
    exit 2
  fi
  [[ -L "$entry" ]] || { echo "Default is not a symlink" >&2; exit 2; }
done

install -d -o root -g root -m 0755 /var/www/fresh-market-price-agent-acme/.well-known/acme-challenge
install -o root -g root -m 0644 "$STAGE/nginx-acme.conf" /etc/nginx/sites-available/fresh-market-price-agent-acme.conf
if [[ -L /etc/nginx/sites-enabled/default ]]; then
    unlink /etc/nginx/sites-enabled/default
fi
ln -s /etc/nginx/sites-available/fresh-market-price-agent-acme.conf /etc/nginx/sites-enabled/fresh-market-price-agent-acme.conf
/usr/sbin/nginx -t
systemctl enable --now nginx.service
systemctl reload nginx.service

install -o root -g root -m 0755 "$STAGE/fresh-market-price-agent-origin-firewall.sh" /usr/local/sbin/fresh-market-price-agent-origin-firewall.sh
install -o root -g root -m 0644 "$STAGE/fresh-market-price-agent-origin-firewall.service" /etc/systemd/system/fresh-market-price-agent-origin-firewall.service
systemctl daemon-reload
systemctl enable --now fresh-market-price-agent-origin-firewall.service
printf 'fresh-market-price-agent-acme-test' > /var/www/fresh-market-price-agent-acme/.well-known/acme-challenge/fresh-market-price-agent-ready
curl -fsS --max-time 4 http://127.0.0.1/.well-known/acme-challenge/fresh-market-price-agent-ready
printf '\nACME_LOOPBACK_OK\n'
curl -sS -m 4 -o /dev/null -w 'PUBLIC_HTTP_MODEL_PATH_STATUS=%{http_code}\n' http://127.0.0.1/v1/forecast
systemctl is-active nginx.service fresh-market-price-agent-origin-firewall.service
/usr/sbin/iptables -S INPUT | grep -F fmpa_forecastengine_origin_v1
