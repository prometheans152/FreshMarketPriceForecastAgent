#!/usr/bin/env bash
# Run manually on Oracle as root in an interactive SSH TTY. The operator
# provides the Tunnel-specific token in a no-echo prompt. No CLI token args,
# environment variable with the token, credential in chat or shell history.
set -euo pipefail
if (( EUID != 0 )); then
  echo 'Use: sudo /usr/local/sbin/tw01-cloudflared-activate' >&2
  exit 1
fi
if [[ ! -t 0 || ! -r /dev/tty ]]; then
  echo 'A human interactive SSH terminal is required; no unattended secrets.' >&2
  exit 2
fi
readonly account_id='aacc8a3a24c5ef00efc530b6845878ce'
readonly tunnel_id='1aa5adeb-6df0-4ba0-ac66-356499e1d6ab'
readonly secret_path='/etc/tw01-cloudflared/token'
if [[ -e "$secret_path" ]]; then
  echo 'TW01 tunnel token file already exists: refusing to overwrite.' >&2
  exit 3
fi
if ! id -u tw01tunnel >/dev/null 2>&1; then
  echo 'Dedicated TW01 tunnel service account was not installed.' >&2
  exit 4
fi
echo 'Use ONLY the token from Cloudflare Tunnel tw01-oraclevpc-20261014.'
echo 'Paste either the entire copied cloudflared service install command'
echo 'or its long eyJ... token. The command is parsed, NEVER executed.'
IFS= read -r -s -p 'TW01 Tunnel install text (input hidden): ' pasted </dev/tty
printf '\n' >/dev/tty
if [[ "$pasted" =~ (eyJ[A-Za-z0-9_+/=-]{75,4096}) ]]; then
  token="${BASH_REMATCH[1]}"
else
  unset pasted
  echo 'No valid Tunnel credential found in pasted input. Nothing saved.' >&2
  exit 5
fi
unset pasted
if (( ${#token} < 80 || ${#token} > 4096 )) ||
    [[ ! "$token" =~ ^eyJ[A-Za-z0-9_+/=-]+$ ]]; then
  unset token
  echo 'Invalid token format or size. No token saved.' >&2
  exit 5
fi
# Check both identifiers locally, without ever printing token/decoded JSON.
if ! printf '%s' "$token" | python3 -c '
import base64,json,sys
s=sys.stdin.read()
data=json.loads(base64.urlsafe_b64decode(s + "="*((4-len(s)%4)%4)))
assert data.get("a") == "aacc8a3a24c5ef00efc530b6845878ce"
assert data.get("t") == "1aa5adeb-6df0-4ba0-ac66-356499e1d6ab"
' >/dev/null 2>&1; then
  unset token
  echo 'Token does not belong to the exact TW01 Cloudflare account and Tunnel.' >&2
  exit 6
fi
umask 077
secret_tmp="$(mktemp /etc/tw01-cloudflared/.token-XXXXXXXX)"
cleanup() {
  [[ -z "${token:-}" ]] || unset token
  [[ -z "${secret_tmp:-}" || ! -e "$secret_tmp" ]] || rm -f "$secret_tmp"
}
trap cleanup EXIT
printf '%s' "$token" > "$secret_tmp"
unset token
chown root:tw01tunnel "$secret_tmp"
chmod 0640 "$secret_tmp"
if [[ -e "$secret_path" ]]; then
  echo 'Concurrent TW01 token install detected; refusing to overwrite.' >&2
  exit 7
fi
mv -n "$secret_tmp" "$secret_path"
secret_tmp=''
systemctl enable --now tw01-cloudflared.service
if ! systemctl is-active --quiet tw01-cloudflared.service; then
  echo 'Tunnel service did not become active. Do not expose forecasts.' >&2
  exit 8
fi
echo 'TW01_TUNNEL_SERVICE_ACTIVE=TRUE; TOKEN_NOT_DISPLAYED'
