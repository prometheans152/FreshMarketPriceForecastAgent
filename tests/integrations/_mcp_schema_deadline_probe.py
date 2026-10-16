"""Genuine SDK client and sacrificial transport for synchronous schema stalls."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import timedelta
from pathlib import Path


def server(directory: Path, project: Path):
    import jsonschema
    from aiot_price.integrations import chatgpt_mcp
    from aiot_price.integrations.chatgpt_contracts import TOOL_SCHEMAS

    original_validate = jsonschema.validate
    original_register = chatgpt_mcp.TransportDeadlineWatchdog.register
    def recorded_register(self, deadline):
        token = original_register(self, deadline)
        (directory / "dispatch.json").write_text(json.dumps({
            "dispatch_start": deadline - 15.0, "work_deadline": deadline,
            "transport_pid": os.getpid(),
        }), encoding="utf-8")
        return token
    def stalled_validate(instance, schema, *args, **kwargs):
        if schema == TOOL_SCHEMAS["post_forecast"]:
            (directory / "entered.json").write_text(json.dumps({
                "validator_entered_at": time.monotonic(), "transport_pid": os.getpid(),
            }), encoding="utf-8")
            time.sleep(17.0)
            (directory / "resumed.json").write_text(json.dumps({
                "validator_resumed": time.monotonic(), "transport_pid": os.getpid(),
            }), encoding="utf-8")
        return original_validate(instance, schema, *args, **kwargs)
    def synthetic_command(*_args):
        code = ('import json,sys; p=json.load(sys.stdin); '
                'r={"tool":p["tool"],"input_echo":p["arguments"],'
                '"normalized_request":None,"query_date":"2026-10-14",'
                '"engine_result":{},"limits":[],"fact_text":"synthetic schema probe"}; '
                'print(json.dumps({"ok":True,"result":r}))')
        return [sys.executable, "-X", "utf8", "-c", code]
    chatgpt_mcp.TransportDeadlineWatchdog.register = recorded_register
    jsonschema.validate = stalled_validate
    chatgpt_mcp._fixed_command = synthetic_command
    # Only this dedicated child enters the transport job, never the SDK client.
    chatgpt_mcp.main([
        "--release-dir", str(project / "models/releases/0.1.0"),
        "--worker-python", sys.executable, "--home", str(directory / "server_home"),
    ])


def process_is_running(pid: int):
    import win32api
    import win32con
    import win32event
    try:
        handle = win32api.OpenProcess(win32con.SYNCHRONIZE, False, pid)
    except Exception as exc:
        if getattr(exc, "winerror", None) == 87:
            return False
        raise
    try:
        return win32event.WaitForSingleObject(handle, 0) == win32con.WAIT_TIMEOUT
    finally:
        handle.Close()


async def client(directory: Path, project: Path):
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    from aiot_price.integrations.chatgpt_mcp import worker_environment
    record = {"synthetic_no_ml": True, "validator_entered": False,
              "returned_success": False, "transport_exit": None}
    env = worker_environment(directory / "transport_home")
    params = StdioServerParameters(command=sys.executable, args=[
        "-X", "utf8", __file__, "server", str(directory), str(project),
    ], env=env, cwd=project)
    async def observe_exit():
        entered_file = directory / "entered.json"
        until = time.monotonic() + 25.0
        while not entered_file.exists():
            if time.monotonic() >= until:
                return
            await asyncio.sleep(0.005)
        entered = json.loads(entered_file.read_text(encoding="utf-8"))
        record.update(entered)
        record["validator_entered"] = True
        pid = entered["transport_pid"]
        while process_is_running(pid):
            if time.monotonic() >= until:
                return
            await asyncio.sleep(0.005)
        record["transport_exit"] = time.monotonic()
    observer = asyncio.create_task(observe_exit())
    started = None
    try:
        with (directory / "server_stderr.log").open("w", encoding="utf-8") as err:
            async with stdio_client(params, errlog=err) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=23)) as session:
                    await session.initialize()
                    started = time.monotonic()
                    result = await session.call_tool("post_forecast", {
                        "crop_id": "cabbage", "market_id": "中義市場",
                        "current_price": 32, "price_unit": "NTD_per_taiwan_jin",
                    })
                    record["returned_success"] = not result.isError
                    record["wire_result"] = result.model_dump(mode="json")
    except BaseException as exc:
        record["exception"] = str(exc)
    finally:
        await observer
    record["client_dispatch_start"] = started
    record["cleanup_completed"] = time.monotonic()
    record["validator_resumed"] = (directory / "resumed.json").exists()
    if (directory / "dispatch.json").exists():
        record.update(json.loads((directory / "dispatch.json").read_text(encoding="utf-8")))
    (directory / "result.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    directory, project = Path(sys.argv[2]), Path(sys.argv[3])
    if sys.argv[1] == "server":
        server(directory, project)
    else:
        asyncio.run(client(directory, project))
