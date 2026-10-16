"""Bounded UTF-8 stdin lines injected into the official MCP stdio transport.

The SDK still parses JSON-RPC and owns the session and stdout. Resource checks
run on raw bytes before decoding or SDK parsing. A limit breach closes this
dedicated transport; the rest of an oversized line is never drained.
"""
from __future__ import annotations

import sys
from typing import BinaryIO

MAX_MCP_MESSAGE_BYTES = 16384  # Includes the newline delimiter.
MAX_MCP_JSON_DEPTH = 16       # Object and array containers combined.
MAX_MCP_OBJECT_MEMBERS = 128  # Across the entire message, not per object.
MAX_MCP_KEY_BYTES = 64        # UTF-8 wire representation, excluding quotes.


class IngressLimitError(ValueError):
    """Fixed-size diagnostic; never include attacker-supplied message text."""


def check_json_bounds(raw: bytes) -> None:
    """Linear lexical preflight, bounded by bytes; the SDK validates JSON syntax.

    Count delimiters only outside quoted strings. Escaped quotes, backslashes,
    colons and container characters inside string values cannot affect bounds.
    Wire key length also bounds escaped-key decoding without allocating keys.
    """
    if len(raw) > MAX_MCP_MESSAGE_BYTES:
        raise IngressLimitError("MCP ingress limit: message_bytes")
    depth = members = 0
    quoted = escaped = False
    string_start = last_string_bytes = 0
    for offset, byte in enumerate(raw):
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:  # backslash
                escaped = True
            elif byte == 34:  # quote
                quoted = False
                last_string_bytes = offset - string_start
            continue
        if byte == 34:
            quoted = True
            string_start = offset + 1
        elif byte in (123, 91):  # object / array open
            depth += 1
            if depth > MAX_MCP_JSON_DEPTH:
                raise IngressLimitError("MCP ingress limit: json_depth")
        elif byte in (125, 93):  # object / array close
            depth -= 1
            if depth < 0:
                raise IngressLimitError("MCP ingress invalid: container")
        elif byte == 58:  # object member separator
            members += 1
            if members > MAX_MCP_OBJECT_MEMBERS:
                raise IngressLimitError("MCP ingress limit: object_members")
            if last_string_bytes > MAX_MCP_KEY_BYTES:
                raise IngressLimitError("MCP ingress limit: key_bytes")


class BoundedStdin:
    """Async text-line interface accepted by mcp.server.stdio.stdio_server.

    readline is called with a hard byte count, before any TextIOWrapper exists.
    A partial line at EOF remains subject to SDK JSON validation, as before.
    Waiting for an idle or partial peer uses a blocking I/O thread, not a CPU
    loop; idle-client timeouts are outside the per-tool work deadline.
    """
    def __init__(self, binary: BinaryIO | None = None):
        self._binary = sys.stdin.buffer if binary is None else binary

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        import anyio
        raw = await anyio.to_thread.run_sync(
            self._binary.readline, MAX_MCP_MESSAGE_BYTES + 1,
        )
        if not raw:
            raise StopAsyncIteration
        check_json_bounds(raw)
        try:
            return raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise IngressLimitError("MCP ingress invalid: utf8") from exc
