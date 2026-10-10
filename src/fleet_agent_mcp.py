"""fleet_agent_mcp - non-breaking import alias for the fleet_agent package.

The distribution (pyproject name) and docs (INSTALL.md) use ``fleet_agent_mcp``,
but the shipped package directory is ``src/fleet_agent`` (renaming it would be
a breaking change: NSSM command lines, imports, and the MCPB stage all point
at ``fleet_agent``). This alias module makes ``python -m fleet_agent_mcp``
behave exactly like ``python -m fleet_agent`` (same argparse surface:
--http/--stdio/--acp/--agentic/--port/--host).

Packaging: shipped in the wheel via [tool.hatch.build.targets.wheel.force-include]
in pyproject.toml. The MCPB bundle manifest keeps ``python -m fleet_agent``
as its entry because the bundle stage contains exactly one package dir.
"""

from fleet_agent.server import main

if __name__ == "__main__":
    main()
