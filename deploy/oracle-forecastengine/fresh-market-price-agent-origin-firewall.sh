#!/usr/bin/env bash
# Only manage individually tagged TCP ports 80 and 443. Preserve all older rules.
set -euo pipefail
mode="${1:-}"
if [[ "$mode" != "ensure" && "$mode" != "remove" ]]; then
  echo "usage: fresh-market-price-agent-origin-firewall.sh ensure|remove" >&2
  exit 2
fi
# Rules installed before the rename carry the legacy tag; "remove" clears both.
tags=(fmpa_forecastengine_origin_v1)
[[ "$mode" == remove ]] && tags+=(tw01_forecastengine_origin_v1)
for port in 80 443; do
  for tag in "${tags[@]}"; do
    args=(-p tcp -m tcp --dport "$port" -m comment --comment "$tag" -j ACCEPT)
    if [[ "$mode" == ensure ]]; then
      /usr/sbin/iptables -C INPUT "${args[@]}" 2>/dev/null || /usr/sbin/iptables -I INPUT 1 "${args[@]}"
    elif /usr/sbin/iptables -C INPUT "${args[@]}" 2>/dev/null; then
      /usr/sbin/iptables -D INPUT "${args[@]}"
    fi
  done
done
printf 'FMPA_FIREWALL_%s=OK\n' "$mode"
