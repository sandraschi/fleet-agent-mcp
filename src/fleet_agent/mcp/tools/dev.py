"""Dev-workflow voice commands — webapp starts, GPU status, InvokeAI engine control.

Fired by the Voice Command Bus: speech-mcp wake -> STT -> fleet-agent
``POST /api/voice/intent`` -> ``fritz`` handlers (voice_command_bus.yaml) -> ``dev_ops``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Annotated, Any, Literal

import httpx
from fastmcp import Context
from pydantic import Field

from ..registry import mcp

logger = logging.getLogger("fleet_agent.tools.dev")

_STARTS_UI_URL = os.environ.get("FLEET_STARTS_UI_URL", "http://127.0.0.1:10791").rstrip("/")
_STARTS_DIR = Path(os.environ.get("FLEET_STARTS_DIR", r"D:\Dev\repos\mcp-central-docs\starts"))
_INVOKEAI_URL = os.environ.get("FLEET_DEV_INVOKEAI_URL", "http://127.0.0.1:11154").rstrip("/")

_PREFIXES = (
    "start webapp",
    "launch webapp",
    "open webapp",
    "boot webapp",
    "start app",
    "start",
    "launch",
    "open",
    "boot",
)
_FILLER = {"please", "for", "me", "now", "up", "the"}


def _clean_repo(raw: str) -> str:
    """Strip spoken command prefixes and filler words from a repo phrase."""
    name = (raw or "").strip().lower()
    for prefix in _PREFIXES:
        if name == prefix or name.startswith(f"{prefix} "):
            name = name[len(prefix) :].strip()
            break
    return " ".join(w for w in name.split() if w not in _FILLER)


def _shortname(file_name: str) -> str:
    name = file_name.lower()
    for suffix in ("-sota-start.bat", "-start.bat"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name.removesuffix(".bat")


def unwrap_bridge(result: dict[str, Any]) -> dict[str, Any]:
    """Extract the inner JSON payload from a fleet_call_tool result."""
    data = result.get("data") if isinstance(result, dict) else None
    for part in (data or {}).get("content") or []:
        if isinstance(part, str):
            try:
                payload = json.loads(part)
                if isinstance(payload, dict):
                    return payload
            except json.JSONDecodeError:
                continue
        elif isinstance(part, dict):
            return part
    return {}


async def _fetch_starts() -> list[dict[str, Any]] | None:
    """Fetch start entries from the Fleet Starts Launcher; None when unreachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{_STARTS_UI_URL}/api/starts")
            resp.raise_for_status()
            data = resp.json()
            entries = data.get("result") if isinstance(data, dict) else None
            if isinstance(entries, list):
                return entries
    except Exception as exc:
        logger.info("Fleet Starts Launcher unreachable (%s); local fallback", exc)
    return None


def _local_starts() -> list[dict[str, Any]]:
    """Scan the starts directory directly (offline fallback for the launcher)."""
    if not _STARTS_DIR.is_dir():
        return []
    return [{"file_name": f.name} for f in sorted(_STARTS_DIR.glob("*.bat"))]


def _match_start(repo: str, entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Best-match a spoken repo phrase against start entries."""
    target = _clean_repo(repo)
    if not target:
        return None
    exact = [e for e in entries if _shortname(str(e.get("file_name", ""))) == target]
    if exact:
        plain = next(
            (e for e in exact if str(e.get("file_name", "")).lower() == f"{target}-start.bat"), None
        )
        return plain or exact[0]
    contains = [e for e in entries if target in _shortname(str(e.get("file_name", "")))]
    if len(contains) == 1:
        return contains[0]
    if len(contains) > 1:
        return None
    starts = sorted(
        e for e in entries if _shortname(str(e.get("file_name", ""))).startswith(target[:4])
    )
    return starts[0] if len(starts) == 1 else None


async def _launch(entry: dict[str, Any]) -> str:
    """Launch via the starts-ui API, falling back to a direct spawn."""
    file_name = str(entry.get("file_name", "")).strip()
    if not file_name:
        raise ValueError("Empty start file name")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{_STARTS_UI_URL}/api/launch", json={"file_name": file_name})
            resp.raise_for_status()
            return file_name
    except Exception as exc:
        logger.info("Launcher POST failed (%s); spawning %s directly", exc, file_name)

    target = _STARTS_DIR / file_name
    if not target.is_file():
        raise FileNotFoundError(f"Start script missing: {target}")
    resolved = target.resolve()

    def _spawn() -> None:
        creationflags = 0x00000010 if os.name == "nt" else 0  # CREATE_NEW_CONSOLE
        subprocess.Popen(
            ["cmd.exe", "/c", str(resolved)] if os.name == "nt" else [str(resolved)],
            cwd=str(resolved.parent),
            creationflags=creationflags,
        )

    await asyncio.to_thread(_spawn)
    return file_name


def _gpu_snapshot() -> dict[str, Any]:
    """Run nvidia-smi in a thread and parse one CSV row per GPU."""
    smi = shutil.which("nvidia-smi")
    if smi is None and os.name == "nt":
        system32 = Path(r"C:\Windows\System32\nvidia-smi.exe")
        if system32.is_file():
            smi = str(system32)
    if smi is None:
        return {"success": False, "error": "nvidia-smi not found", "error_type": "not_found"}
    query = (
        "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,"
        "temperature.gpu,power.draw",
        "--format=csv,noheader,nounits",
    )
    try:
        proc = subprocess.run(
            [smi, *query],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"success": False, "error": f"nvidia-smi failed: {exc}", "error_type": "exec"}
    if proc.returncode != 0:
        return {
            "success": False,
            "error": (proc.stderr or "nvidia-smi error").strip()[:300],
            "error_type": "exec",
        }
    gpus: list[dict[str, Any]] = []
    for line in proc.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 7:
            continue
        try:
            gpus.append(
                {
                    "index": int(parts[0]),
                    "name": parts[1],
                    "utilization_pct": int(parts[2]) if parts[2].isdigit() else None,
                    "vram_used_mb": int(parts[3]),
                    "vram_total_mb": int(parts[4]),
                    "temperature_c": int(parts[5]) if parts[5].isdigit() else None,
                    "power_w": float(parts[6]) if parts[6] else None,
                }
            )
        except ValueError:
            logger.warning("Unparsable nvidia-smi row: %s", line)
    if not gpus:
        return {"success": False, "error": "No NVIDIA GPU detected", "error_type": "no_gpu"}
    return {"success": True, "gpus": gpus}


async def _opencode_send(prompt: str) -> dict[str, Any]:
    """Send a spoken task to the most recently active opencode session."""
    from .fleet_bridge import fleet_call_tool

    text = (prompt or "").strip()
    if text.lower().startswith("opencode"):
        text = text[len("opencode") :].strip(" ,.")
    if not text:
        return {
            "success": False,
            "message": "Say what opencode should do, e.g. 'opencode assfix devices'.",
            "error_type": "validation",
        }
    listed = await fleet_call_tool(server="opencode", tool="opencode_list_sessions", arguments={})
    sessions = (unwrap_bridge(listed).get("data") or {}).get("sessions") or []
    if not sessions:
        message = str(unwrap_bridge(listed).get("message") or "")
        return {
            "success": False,
            "message": message or "No opencode sessions found - start opencode first.",
            "error_type": "no_session",
        }

    def _sort_key(s: Any) -> int | float:
        t = (s or {}).get("time") or {}
        return t.get("updated") or t.get("created") or 0

    target = max(sessions, key=_sort_key)
    session_id = str(target.get("id", ""))
    title = str(target.get("title") or session_id)
    sent = await fleet_call_tool(
        server="opencode",
        tool="opencode_send_message",
        arguments={"session_id": session_id, "message": text},
    )
    payload = unwrap_bridge(sent)
    if not sent.get("success") or not payload.get("success", True):
        return {
            "success": False,
            "message": str(payload.get("message") or "Failed to send message to opencode session."),
            "error_type": "send_failed",
        }
    return {"success": True, "message": f"Sent to opencode session '{title}': {text}"}


async def _gpu_status() -> dict[str, Any]:
    snap = await asyncio.to_thread(_gpu_snapshot)
    if not snap.get("success"):
        return {
            "success": False,
            "message": snap.get("error", "GPU status unavailable"),
            "error": snap.get("error"),
            "error_type": snap.get("error_type"),
        }
    parts: list[str] = []
    for g in snap["gpus"]:
        used_gb = g["vram_used_mb"] / 1024
        total_gb = g["vram_total_mb"] / 1024
        load = g["utilization_pct"] if g["utilization_pct"] is not None else 0
        temp = g["temperature_c"] if g["temperature_c"] is not None else 0
        parts.append(
            f"{g['name']}: {load}% load, {used_gb:.1f} of {total_gb:.0f} GB VRAM, {temp} C"
        )
    return {
        "success": True,
        "message": "; ".join(parts),
        "data": {"gpus": snap["gpus"]},
    }


async def _invokeai_kick() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{_INVOKEAI_URL}/api/invokeai/engine/start")
            resp.raise_for_status()
            data = resp.json() if resp.text else {}
    except httpx.ConnectError:
        return {
            "success": False,
            "message": (
                "invokeai-mcp is not running; start it first with 'fritz start webapp invokeai'."
            ),
            "error_type": "offline",
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"InvokeAI engine start failed: {exc}",
            "error_type": "http",
        }
    if not isinstance(data, dict) or not data.get("success"):
        return {
            "success": False,
            "message": str(data.get("message") or data.get("error") or "Engine start failed"),
        }
    return {"success": True, "message": str(data.get("message", "InvokeAI engine starting."))}


async def _invokeai_status() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{_INVOKEAI_URL}/api/invokeai/engine/status")
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError:
        return {
            "success": False,
            "message": (
                "invokeai-mcp is not running; start it first with 'fritz start webapp invokeai'."
            ),
            "error_type": "offline",
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"InvokeAI engine status failed: {exc}",
            "error_type": "http",
        }
    running = bool(data.get("running")) if isinstance(data, dict) else False
    pid = data.get("pid") if isinstance(data, dict) else None
    return {
        "success": True,
        "message": f"InvokeAI engine is {'running' if running else 'stopped'}"
        + (f" (pid {pid})" if running and pid else ""),
        "data": data,
    }


async def _start_webapp(repo: str) -> dict[str, Any]:
    entries = await _fetch_starts()
    local_mode = entries is None
    if entries is None:
        entries = _local_starts()
    match = _match_start(repo, entries)
    target = _clean_repo(repo)
    if match is None:
        names = sorted({_shortname(str(e.get("file_name", ""))) for e in entries})
        suggestion = next((n for n in names if target and n.startswith(target[:4])), None)
        hint = f" Did you mean {suggestion}?" if suggestion else ""
        return {
            "success": False,
            "message": f"No webapp start script matched '{target}'.{hint}",
            "error_type": "no_match",
        }
    try:
        file_name = await _launch(match)
    except (FileNotFoundError, ValueError) as exc:
        return {"success": False, "message": str(exc), "error_type": "launch"}
    label = str(match.get("title") or "").strip() or _shortname(file_name)
    via = "directly" if local_mode else "via Fleet Starts Launcher"
    return {"success": True, "message": f"{label} webapp starting ({via})."}


async def _list_webapps() -> dict[str, Any]:
    entries = await _fetch_starts()
    if entries is None:
        entries = _local_starts()
    webapps = sorted(
        [
            {
                "shortname": _shortname(str(e.get("file_name", ""))),
                "title": str(e.get("title") or "").strip(),
                "port": e.get("port"),
            }
            for e in entries
            if str(e.get("file_name", "")).endswith(".bat")
        ],
        key=lambda w: w["shortname"],
    )
    return {
        "success": True,
        "message": f"{len(webapps)} webapps available. Say 'fritz start webapp <name>'.",
        "data": {"webapps": webapps},
    }


@mcp.tool(annotations={"readOnly": False}, version="0.1.0")
async def dev_ops(
    operation: Annotated[
        Literal[
            "start_webapp",
            "gpu_status",
            "invokeai_kick",
            "invokeai_status",
            "list_webapps",
            "opencode_send",
        ],
        Field(description="Dev command to execute."),
    ],
    repo: Annotated[
        str | None,
        Field(
            description=(
                "Webapp name for start_webapp (spoken phrase OK, e.g. 'start webapp arxiv')."
            )
        ),
    ] = None,
    prompt: Annotated[
        str | None,
        Field(description="Spoken task for opencode_send (after the word 'opencode')."),
    ] = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Run dev-workflow commands from the voice command bus.

    [RATIONALE]
    One portmanteau covers the spoken dev commands (webapp starts, GPU status,
    InvokeAI engine control, opencode delegation) so the voice registry can
    route all of them to a single always-on daemon (fleet-agent) without
    per-command tools.

    Operations:
    - start_webapp: launch a fleet webapp stack via the Fleet Starts Launcher
      (falls back to a direct spawn when the launcher is down).
    - gpu_status: nvidia-smi snapshot (load, VRAM, temperature per GPU).
    - invokeai_kick: start the InvokeAI engine via invokeai-mcp REST.
    - invokeai_status: running/stopped state of the InvokeAI engine.
    - list_webapps: catalog of startable webapps for voice routing errors.
    - opencode_send: send the spoken task to the most recently active
      opencode session (the one currently open in the TUI).

    ## Return Format
    {"success": bool, "message": str, "data"?: {...}, "error"?: str,
     "error_type"?: str}

    ## Examples
    dev_ops(operation="gpu_status")
    dev_ops(operation="start_webapp", repo="start webapp arxiv")
    dev_ops(operation="invokeai_kick")
    dev_ops(operation="opencode_send", prompt="opencode assfix devices, run")
    """
    if operation == "gpu_status":
        return await _gpu_status()
    if operation == "invokeai_kick":
        return await _invokeai_kick()
    if operation == "invokeai_status":
        return await _invokeai_status()
    if operation == "list_webapps":
        return await _list_webapps()
    if operation == "opencode_send":
        return await _opencode_send(prompt or "")
    if operation == "start_webapp":
        if not repo or not repo.strip():
            return {
                "success": False,
                "message": "Say which webapp, e.g. 'fritz start webapp arxiv'.",
                "error_type": "validation",
            }
        return await _start_webapp(repo)
    return {
        "success": False,
        "message": f"Unknown operation: {operation}",
        "error_type": "validation",
    }
