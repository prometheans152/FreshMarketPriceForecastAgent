#!/usr/bin/env bash
# Only manage individually tagged TCP ports 80 and 443. Preserve all older rules.
set -euo pipefail
mode="${1:-}"
if [[ "$mode" != "ensure" && "$mode" != "remove" ]]; then
  echo "usage: tw01-origin-firewall.sh ensure|remove" >&2
  exit 2
fi
for port in 80 443; do
  args=(-p tcp -m tcp --dport "$port" -m comment --comment "tw01_forecastengine_origin_v1" -j ACCEPT)
  if [[ "$mode" == ensure ]]; then
    /usr/sbin/iptables -C INPUT "${args[@]}" 2>/dev/null || /usr/sbin/iptables -I INPUT 1 "${args[@]}"
  else
    if /usr/sbin/iptables -C INPUT "${args[@]}" 2>/dev/null; then
      /usr/sbin/iptables -D INPUT "${args[@]}"
    fi
  fi
done
printf 'TW01_FIREWALL_%s=OK\n' "$mode"
