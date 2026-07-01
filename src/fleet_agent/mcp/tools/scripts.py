"""Script management tools — CRUD + execution for task scripts.

Supports Python and shell scripts with sandboxed execution and output capture.
Scripts can be linked to tasks and run on schedule.
"""

import asyncio
import json
import traceback
from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from ...engine.sqlite_store import get_store
from ..registry import mcp

_LANG_MAP = {"python": "py", "shell": "bat", "powershell": "ps1"}


@mcp.tool(annotations={"readonly": False}, version="0.1.0")
async def script_create(
    name: Annotated[str, Field(description="Human-readable script name.")],
    content: Annotated[str, Field(description="Script source code.")],
    language: Annotated[str, Field(description="Language: python, shell, or powershell.")] = "python",
    description: Annotated[str, Field(description="What this script does.")] = "",
) -> dict[str, Any]:
    """Create a new task script.

    ## Return Format
    {"success": bool, "script": dict, "message": str}

    ## Examples
    script_create(name="Fleet Health Check", content="...", language="python")
    """
    store = get_store()
    script = store.script_create(name=name, content=content, language=language, description=description)
    return {"success": True, "script": script, "message": f"Script '{name}' created (id: {script['id']})."}


@mcp.tool(annotations={"readonly": True}, version="0.1.0")
async def script_get(
    script_id: Annotated[str, Field(description="Script ID.")],
) -> dict[str, Any]:
    """Get a script by ID.

    ## Return Format
    {"success": bool, "script": dict, "message": str}
    """
    store = get_store()
    script = store.script_get(script_id)
    if not script:
        return {"success": False, "message": f"Script '{script_id}' not found."}
    return {"success": True, "script": script, "message": f"Script: {script['name']}"}


@mcp.tool(annotations={"readonly": False}, version="0.1.0")
async def script_update(
    script_id: Annotated[str, Field(description="Script ID to update.")],
    name: Annotated[str | None, Field(description="New name.")] = None,
    description: Annotated[str | None, Field(description="New description.")] = None,
    content: Annotated[str | None, Field(description="New source code.")] = None,
    language: Annotated[str | None, Field(description="New language.")] = None,
) -> dict[str, Any]:
    """Update an existing script.

    ## Return Format
    {"success": bool, "script": dict, "message": str}
    """
    store = get_store()
    kwargs = {k: v for k, v in [("name", name), ("description", description), ("content", content), ("language", language)] if v is not None}
    script = store.script_update(script_id, **kwargs)
    if not script:
        return {"success": False, "message": f"Script '{script_id}' not found."}
    return {"success": True, "script": script, "message": f"Script '{script['name']}' updated."}


@mcp.tool(annotations={"readonly": False, "destructive": True}, version="0.1.0")
async def script_delete(
    script_id: Annotated[str, Field(description="Script ID to delete.")],
) -> dict[str, Any]:
    """Delete a script permanently.

    ## Return Format
    {"success": bool, "message": str}
    """
    store = get_store()
    if store.script_delete(script_id):
        return {"success": True, "message": f"Script '{script_id}' deleted."}
    return {"success": False, "message": f"Script '{script_id}' not found."}


@mcp.tool(annotations={"readonly": True}, version="0.1.0")
async def script_list() -> dict[str, Any]:
    """List all registered scripts.

    ## Return Format
    {"success": bool, "scripts": list[dict], "count": int, "message": str}
    """
    store = get_store()
    scripts = store.script_list()
    return {
        "success": True,
        "scripts": scripts,
        "count": len(scripts),
        "message": f"{len(scripts)} script(s) registered.",
    }


@mcp.tool(annotations={"readonly": False}, version="0.1.0")
async def script_run(
    script_id: Annotated[str, Field(description="Script ID to execute.")],
    args: Annotated[str | None, Field(description="Optional JSON arguments passed to script execution context.")] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """Run a script and return its output.

    Python scripts: executed via exec() with a __result dict and __log list.
    Shell scripts: run via subprocess with 30s timeout.
    PowerShell scripts: run via pwsh -Command with 30s timeout.

    ## Return Format
    {"success": bool, "stdout": str, "stderr": str, "result": any, "exit_code": int, "message": str}

    ## Examples
    script_run("a1b2c3d4")
    """
    store = get_store()
    script = store.script_get(script_id)
    if not script:
        return {"success": False, "message": f"Script '{script_id}' not found."}

    lang = script.get("language", "python")
    content = script["content"]
    parsed_args: dict = {}
    if args:
        try:
            parsed_args = json.loads(args)
        except json.JSONDecodeError:
            return {"success": False, "message": "Invalid JSON in args."}

    stdout_buf: list[str] = []
    stderr_buf: list[str] = []
    result = None

    try:
        if lang == "mcp_call":
            spec = json.loads(content)
            server_name = spec.get("server", "")
            tool_name = spec.get("tool", "")
            params = spec.get("params", {})
            from .fleet_bridge import fleet_call_tool
            call_result = await fleet_call_tool(server=server_name, tool=tool_name, arguments=params)
            stdout_buf.append(json.dumps(call_result.get("data", {}), indent=2))
            result = call_result
            ec = 0 if call_result.get("success") else 1

            # Optional LLM analysis of the tool result
            llm_prompt = spec.get("llm_analyze")
            if llm_prompt and call_result.get("success"):
                try:
                    from ...llm_client import chat_completion
                    tool_output = json.dumps(call_result, indent=2)
                    analysis = await chat_completion([
                        {"role": "system", "content": "You are Fritz, a fleet conductor agent. Analyze the following tool output concisely and provide actionable insights."},
                        {"role": "user", "content": f"Tool: {tool_name} on {server_name}\n\nResult:\n{tool_output}\n\nTask: {llm_prompt}"},
                    ])
                    stdout_buf.append(f"\n--- AI Analysis ---\n{analysis}")
                    result = {"tool_result": call_result, "analysis": analysis}
                except Exception as llm_err:
                    stdout_buf.append(f"\n--- AI Analysis unavailable: {llm_err} ---")
        elif lang == "python":
            _result: dict[str, Any] = {}
            _log: list[str] = []
            _ns = {
                "__result": _result,
                "__log": _log,
                "__args": parsed_args,
                "print": lambda *a, **kw: _log.append(" ".join(str(x) for x in a)),
            }
            exec(content, _ns)  # noqa: S102
            stdout_buf = _log
            result = _result
        elif lang == "powershell":
            proc = await asyncio.create_subprocess_exec(
                "pwsh", "-NoProfile", "-Command", content,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                out, err = await asyncio.wait_for(proc.communicate(), timeout=30)
                stdout_buf = out.decode("utf-8", errors="replace").splitlines()
                stderr_buf = err.decode("utf-8", errors="replace").splitlines()
            except TimeoutError:
                proc.kill()
                return {"success": False, "stdout": "", "stderr": "Timeout (30s)", "result": None, "exit_code": -1, "message": "Script timed out"}
        else:
            proc = await asyncio.create_subprocess_shell(
                content,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                out, err = await asyncio.wait_for(proc.communicate(), timeout=30)
                stdout_buf = out.decode("utf-8", errors="replace").splitlines()
                stderr_buf = err.decode("utf-8", errors="replace").splitlines()
            except TimeoutError:
                proc.kill()
                return {"success": False, "stdout": "", "stderr": "Timeout (30s)", "result": None, "exit_code": -1, "message": "Script timed out"}
        ec = 0
    except Exception as e:
        stderr_buf.append(f"{type(e).__name__}: {e}")
        stderr_buf.extend(traceback.format_exc().splitlines())
        ec = 1

    return {
        "success": ec == 0,
        "stdout": "\n".join(stdout_buf),
        "stderr": "\n".join(stderr_buf),
        "result": result,
        "exit_code": ec,
        "message": f"Script '{script['name']}' exited with code {ec}.",
    }


@mcp.tool(annotations={"readOnly": True}, version="0.1.0")
async def script_generate(
    prompt: Annotated[str, Field(description="Natural language description of what the script should do.")],
) -> dict[str, Any]:
    """Use the LLM to generate a task script from a natural language prompt.

    The LLM chooses the best language (python, mcp_call, shell, or powershell)
    and generates the script content, a suggested name, and description.
    For mcp_call scripts, it selects the appropriate server, tool, and params.

    ## Return Format
    {"success": bool, "name": str, "description": str, "language": str, "content": str, "message": str}

    ## Examples
    script_generate(prompt="Check all fleet servers health and email a summary")
    script_generate(prompt="Every hour, check cursor spend and alert if over $50")
    """
    from ...llm_client import chat_completion

    # Build fleet server context for the LLM
    from .fleet_bridge import FLEET_SERVERS

    server_tools_list = "\n".join(
        f"  - {alias}: {info['description']} (tools: {', '.join(info.get('key_tools', ['?']))})"
        for alias, info in FLEET_SERVERS.items()
    )

    system_prompt = (
        "You are an expert script generator for a fleet MCP agent system called Fritz. "
        "Given a natural language request, generate a script that accomplishes it.\n\n"
        "Available script languages:\n"
        "  - python:    Full Python code (use when complex logic or custom computation is needed)\n"
        "  - mcp_call:  Call an MCP tool on a fleet server. Content is JSON with server, tool, params, and optional llm_analyze.\n"
        "  - shell:     Windows shell commands (use for file ops, system commands)\n"
        "  - powershell: PowerShell script\n\n"
        "Available fleet servers:\n"
        f"{server_tools_list}\n\n"
        "For mcp_call scripts, the content JSON has this structure:\n"
        '{"server": "server-alias", "tool": "tool_name", "params": {"key": "value"}, "llm_analyze": "optional prompt for Fritz to analyze the result"}\n\n'
        "IMPORTANT: Respond ONLY with a JSON object. No markdown, no explanation:\n"
        '{"name": "Short name", "description": "What it does", "language": "python|mcp_call|shell|powershell", "content": "the script body"}'
    )

    try:
        response = await chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ])
    except Exception as e:
        return {"success": False, "message": f"LLM unavailable: {e}", "name": "", "description": "", "language": "python", "content": ""}

    import json as _json
    import re as _re
    match = _re.search(r"\{.*\}", response, _re.DOTALL)
    if not match:
        return {"success": False, "message": "LLM did not return valid JSON", "name": "", "description": "", "language": "python", "content": response[:1000]}

    try:
        result = _json.loads(match.group(0))
        name = result.get("name", "Generated Script")
        desc = result.get("description", "")
        lang = result.get("language", "python")
        content_raw = result.get("content", "")
        if lang == "mcp_call":
            content_out = content_raw if isinstance(content_raw, str) else _json.dumps(content_raw, indent=2)
        else:
            content_out = str(content_raw)
        return {
            "success": True,
            "name": name,
            "description": desc,
            "language": lang,
            "content": content_out,
            "message": f"Generated '{name}' ({lang}).",
        }
    except (_json.JSONDecodeError, KeyError) as e:
        return {"success": False, "message": f"Failed to parse LLM output: {e}", "name": "", "description": "", "language": "python", "content": response[:1000]}
