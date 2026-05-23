"""Teleport tools — pack agent identity + memory + workflows for migration.

Inspired by kagura-agent/openclaw-teleport: packs everything that makes an agent
"that agent" into a single portable file. Unpack on new machine = full restore.
"""

import json
import tarfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from ...config import settings
from ..registry import mcp


def _list_files(directory: Path) -> list[str]:
    if not directory.exists():
        return []
    files = []
    for p in directory.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            files.append(str(p.relative_to(directory.parent)))
    return files


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def teleport_pack(
    output_path: Annotated[
        str | None,
        Field(
            description=(
                "Output path for .soul file. "
                "Defaults to ~/.fleet-agent/{name}_{date}.soul."
            ),
        ),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Pack agent identity, memory, workflows, and config into a portable .soul archive.

    The .soul file contains everything needed to restore the agent on another machine.
    WARNING: .soul files may contain sensitive config data. Treat them like password files.

    ## Return Format
    {"success": bool, "soul_path": str, "file_count": int, "manifest": dict, "message": str}

    ## Examples
    teleport_pack()
    teleport_pack(output_path="/tmp/lumen_backup.soul")
    """
    date_str = datetime.now(UTC).strftime("%Y%m%d")
    name = settings.agent_name.lower()
    soul_path = output_path or str(Path.home() / ".fleet-agent" / f"{name}_{date_str}.soul")

    manifest = {
        "agent_name": settings.agent_name,
        "human_name": settings.human_name,
        "version": "0.1.0",
        "packed_at": datetime.now(UTC).isoformat(),
        "id": str(uuid.uuid4())[:8],
    }

    files_to_pack: list[tuple[str, Path]] = []

    # Identity files
    ident_dir = settings.project_root / "identity"
    user_ident_dir = Path.home() / ".fleet-agent" / "identity"
    for d in [ident_dir, user_ident_dir]:
        for fname in ["SOUL.md", "NORTH_STAR.md", "USER.md"]:
            fp = d / fname
            if fp.exists():
                files_to_pack.append((f"identity/{fname}", fp))

    # Workflow files
    wf_dir = settings.project_root / "workflows"
    user_wf_dir = Path.home() / ".fleet-agent" / "workflows"
    for d in [wf_dir, user_wf_dir]:
        if d.exists():
            for fp in d.glob("*.yaml"):
                files_to_pack.append((f"workflows/{fp.name}", fp))
            for fp in d.glob("*.yml"):
                files_to_pack.append((f"workflows/{fp.name}", fp))

    # SQLite database (contains workflows, tasks, memory cards, evolution log)
    db_path = settings.db_path
    if db_path.exists():
        files_to_pack.append(("data/fleet-agent.db", db_path))

    # Memory markdown files
    mem_dir = settings.project_root / "memory"
    if mem_dir.exists():
        for fp in mem_dir.rglob("*.md"):
            if ".git" not in fp.parts:
                rel = fp.relative_to(settings.project_root)
                files_to_pack.append((f"memory/{rel.relative_to('memory')}", fp))

    manifest["file_count"] = len(files_to_pack)

    # Create tar.gz
    Path(soul_path).parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(soul_path, "w:gz") as tar:
        # Write manifest
        manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
        import io
        manifest_tarinfo = tarfile.TarInfo(name="manifest.json")
        manifest_tarinfo.size = len(manifest_bytes)
        tar.addfile(manifest_tarinfo, io.BytesIO(manifest_bytes))

        # Write files
        for arcname, filepath in files_to_pack:
            tar.add(str(filepath), arcname=arcname)

    return {
        "success": True,
        "soul_path": soul_path,
        "file_count": len(files_to_pack),
        "manifest": manifest,
        "includes": ["identity", "workflows", "memory", "database"],
        "message": f"Agent packed to '{soul_path}' ({len(files_to_pack)} files).",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def teleport_inspect(
    soul_path: Annotated[str, Field(description="Path to .soul file to inspect.")],
    ctx: Context = None,
) -> dict[str, Any]:
    """Inspect a .soul archive without unpacking — show manifest and file listing.

    ## Return Format
    {"success": bool, "manifest": dict, "files": list[str], "message": str}

    ## Examples
    teleport_inspect("lumen_20260519.soul")
    """
    try:
        with tarfile.open(soul_path, "r:gz") as tar:
            files = [m.name for m in tar.getmembers() if m.name != "manifest.json"]

            manifest = {}
            try:
                mf = tar.extractfile("manifest.json")
                if mf:
                    manifest = json.loads(mf.read().decode("utf-8"))
            except KeyError:
                pass

            return {
                "success": True,
                "manifest": manifest,
                "files": files,
                "file_count": len(files),
                "message": f"Soul archive contains {len(files)} files.",
            }
    except FileNotFoundError:
        return {"success": False, "message": f"Soul file not found: {soul_path}"}
    except Exception as e:
        return {"success": False, "message": f"Failed to inspect: {e}"}


@mcp.tool(annotations={"readOnly": False, "destructive": True}, version="0.1.0")
async def teleport_unpack(
    soul_path: Annotated[str, Field(description="Path to .soul file to unpack.")],
    target_dir: Annotated[
        str | None,
        Field(
            description=(
                "Target directory for unpacking. "
                "Defaults to ~/.fleet-agent/."
            ),
        ),
    ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Unpack a .soul archive — restore agent identity, memory, workflows, and database.

    WARNING: Overwrites existing files in the target directory.
    DESTRUCTIVE operation — creates/overwrites database and files.

    ## Return Format
    {"success": bool, "files_restored": int, "target_dir": str, "message": str}

    ## Examples
    teleport_unpack("lumen_20260519.soul")
    """
    target = Path(target_dir) if target_dir else Path.home() / ".fleet-agent"
    target.mkdir(parents=True, exist_ok=True)

    try:
        files_restored = 0
        with tarfile.open(soul_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name == "manifest.json":
                    continue
                dest = target / member.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                f = tar.extractfile(member)
                if f:
                    dest.write_bytes(f.read())
                    files_restored += 1

        return {
            "success": True,
            "files_restored": files_restored,
            "target_dir": str(target),
            "message": f"Unpacked {files_restored} files to '{target}'. Agent restored.",
        }
    except FileNotFoundError:
        return {"success": False, "message": f"Soul file not found: {soul_path}"}
    except Exception as e:
        return {"success": False, "message": f"Failed to unpack: {e}"}
