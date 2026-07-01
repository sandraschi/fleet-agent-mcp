# fleet-agent-mcp (MCPB Bundle)

Self-evolving AI agent — state machine, task management, knowledge accumulation, identity. Inspired by kagura-agent.

## Usage

Add to \claude_desktop_config.json\:
\\\json
{
  "mcpServers": {
    "fleet-agent-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "\D:\Dev\repos", "python", "-m", "fleet_agent_mcp"],
      "env": { "PYTHONPATH": "\D:\Dev\repos/src" }
    }
  }
}
\\\

## Tools

- **fleet-agent-mcp**: Self-evolving AI agent — state machine, task management, knowledge accumulation, identity. Inspired by kagura-agent.

## Requirements

- Python 3.12+
- uv
