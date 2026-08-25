# Fritz Agent User Guide, Workflows & Operational Tutorials

Welcome to the comprehensive user guide for **fleet-agent-mcp** (Fritz). This manual provides step-by-step tutorials, workflow guides, voice command tutorials, and troubleshooting procedures for operating Fritz across terminal sessions, web applications, and desktop environments.

## 1. Quick Start & Installation
Fritz can be executed via `start.ps1`, `just`, or as a desktop application. When running locally, Fritz exposes three HTTP/REST ports:
- **10996**: FastMCP 3.2 HTTP server and REST endpoints (`/api/health`, `/api/v1/diagnostics`, `/mcp`).
- **10997**: React + Vite Web App operator dashboard.
- **11027**: Shared Intel Reports Hub HTML index for iPad / Tailscale reading.

## 2. Step-by-Step Tutorials

### Tutorial: Master the `flowforge` Subsystem
In this tutorial, you will learn how to effectively use the `11` tools provided by the `flowforge` subsystem.
**Overview**: YAML-defined state machine with gate enforcement and anti-spin failure limit auto-blocking.
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `flowforge`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using flowforge
just flowforge-demo
```

### Tutorial: Master the `pulse` Subsystem
In this tutorial, you will learn how to effectively use the `6` tools provided by the `pulse` subsystem.
**Overview**: Task management with north-star alignment, priority ordering, and stale task detection.
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `pulse`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using pulse
just pulse-demo
```

### Tutorial: Master the `memory` Subsystem
In this tutorial, you will learn how to effectively use the `8` tools provided by the `memory` subsystem.
**Overview**: Compile-time knowledge wiki, card linting, project notes, and external SKILL.md importer.
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `memory`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using memory
just memory-demo
```

### Tutorial: Master the `identity` Subsystem
In this tutorial, you will learn how to effectively use the `4` tools provided by the `identity` subsystem.
**Overview**: Agent self-definition (SOUL.md, NORTH_STAR.md, USER.md) and purpose alignment.
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `identity`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using identity
just identity-demo
```

### Tutorial: Master the `teleport` Subsystem
In this tutorial, you will learn how to effectively use the `3` tools provided by the `teleport` subsystem.
**Overview**: Soul migration system (pack, inspect, unpack .soul tar.gz archives).
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `teleport`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using teleport
just teleport-demo
```

### Tutorial: Master the `evolution` Subsystem
In this tutorial, you will learn how to effectively use the `3` tools provided by the `evolution` subsystem.
**Overview**: Mistake log, correction tracking, and lesson extraction.
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `evolution`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using evolution
just evolution-demo
```

### Tutorial: Master the `heartbeat` Subsystem
In this tutorial, you will learn how to effectively use the `3` tools provided by the `heartbeat` subsystem.
**Overview**: Agent wake-up routine, health check, and open-weight pipeline liveness probing.
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `heartbeat`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using heartbeat
just heartbeat-demo
```

### Tutorial: Master the `fleet_bridge` Subsystem
In this tutorial, you will learn how to effectively use the `4` tools provided by the `fleet_bridge` subsystem.
**Overview**: Cross-server MCP client, tool discovery, and repo inspection across 19 fleet servers.
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `fleet_bridge`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using fleet_bridge
just fleet_bridge-demo
```

### Tutorial: Master the `codegen` Subsystem
In this tutorial, you will learn how to effectively use the `3` tools provided by the `codegen` subsystem.
**Overview**: LLM code generation, direct file writing, and surgical file editing with .bak backups.
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `codegen`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using codegen
just codegen-demo
```

### Tutorial: Master the `github` Subsystem
In this tutorial, you will learn how to effectively use the `9` tools provided by the `github` subsystem.
**Overview**: Full PR lifecycle automation (branch, commit, push, PR, review, merge, status).
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `github`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using github
just github-demo
```

### Tutorial: Master the `contribute` Subsystem
In this tutorial, you will learn how to effectively use the `1` tools provided by the `contribute` subsystem.
**Overview**: Autonomous open-source PR pipeline (study -> branch -> fix -> test -> PR).
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `contribute`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using contribute
just contribute-demo
```

### Tutorial: Master the `notify` Subsystem
In this tutorial, you will learn how to effectively use the `3` tools provided by the `notify` subsystem.
**Overview**: Email notification dispatch and cron heartbeat scheduling.
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `notify`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using notify
just notify-demo
```

### Tutorial: Master the `coworker` Subsystem
In this tutorial, you will learn how to effectively use the `3` tools provided by the `coworker` subsystem.
**Overview**: Scheduled office + fleet coworker flows (Fleet Pulse, Day Prep, Weekly PDF, Board Pack).
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `coworker`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using coworker
just coworker-demo
```

### Tutorial: Master the `intel_hub` Subsystem
In this tutorial, you will learn how to effectively use the `3` tools provided by the `intel_hub` subsystem.
**Overview**: Shared HTML Intel Reports Hub (port 11027) and AIWatcher event push.
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `intel_hub`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using intel_hub
just intel_hub-demo
```

### Tutorial: Master the `voice` Subsystem
In this tutorial, you will learn how to effectively use the `2` tools provided by the `voice` subsystem.
**Overview**: Voice Command Bus intent router across fleet receivers.
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `voice`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using voice
just voice-demo
```

### Tutorial: Master the `scripts` Subsystem
In this tutorial, you will learn how to effectively use the `7` tools provided by the `scripts` subsystem.
**Overview**: Script CRUD, execution, MCP tool call builder, and LLM script generation.
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `scripts`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using scripts
just scripts-demo
```

### Tutorial: Master the `dev` Subsystem
In this tutorial, you will learn how to effectively use the `1` tools provided by the `dev` subsystem.
**Overview**: Dev-ops voice commands (webapp starts, GPU status, InvokeAI, opencode).
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `dev`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using dev
just dev-demo
```

### Tutorial: Master the `assist` Subsystem
In this tutorial, you will learn how to effectively use the `1` tools provided by the `assist` subsystem.
**Overview**: Domestic voice intents (timers, Plex playback, VLC stream, Calibre book search).
#### Instructions:
1. Open the Fritz webapp dashboard at `http://127.0.0.1:10997` or connect your MCP client.
2. Trigger the primary tool for `assist`.
3. Verify output in the logger tab or SQLite execution log.
#### Practical Example:
```powershell
# Execute a task using assist
just assist-demo
```

## Advanced Workflow Guide #1: Autonomous Operation & Deep Integration
In workflow guide #1, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #2: Autonomous Operation & Deep Integration
In workflow guide #2, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #3: Autonomous Operation & Deep Integration
In workflow guide #3, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #4: Autonomous Operation & Deep Integration
In workflow guide #4, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #5: Autonomous Operation & Deep Integration
In workflow guide #5, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #6: Autonomous Operation & Deep Integration
In workflow guide #6, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #7: Autonomous Operation & Deep Integration
In workflow guide #7, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #8: Autonomous Operation & Deep Integration
In workflow guide #8, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #9: Autonomous Operation & Deep Integration
In workflow guide #9, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #10: Autonomous Operation & Deep Integration
In workflow guide #10, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #11: Autonomous Operation & Deep Integration
In workflow guide #11, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #12: Autonomous Operation & Deep Integration
In workflow guide #12, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #13: Autonomous Operation & Deep Integration
In workflow guide #13, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #14: Autonomous Operation & Deep Integration
In workflow guide #14, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #15: Autonomous Operation & Deep Integration
In workflow guide #15, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #16: Autonomous Operation & Deep Integration
In workflow guide #16, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #17: Autonomous Operation & Deep Integration
In workflow guide #17, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #18: Autonomous Operation & Deep Integration
In workflow guide #18, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #19: Autonomous Operation & Deep Integration
In workflow guide #19, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #20: Autonomous Operation & Deep Integration
In workflow guide #20, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #21: Autonomous Operation & Deep Integration
In workflow guide #21, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #22: Autonomous Operation & Deep Integration
In workflow guide #22, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #23: Autonomous Operation & Deep Integration
In workflow guide #23, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #24: Autonomous Operation & Deep Integration
In workflow guide #24, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #25: Autonomous Operation & Deep Integration
In workflow guide #25, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #26: Autonomous Operation & Deep Integration
In workflow guide #26, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #27: Autonomous Operation & Deep Integration
In workflow guide #27, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #28: Autonomous Operation & Deep Integration
In workflow guide #28, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.

## Advanced Workflow Guide #29: Autonomous Operation & Deep Integration
In workflow guide #29, we explore how to configure background scheduled tasks, set up multi-source intelligence ingestion, and leverage Fritz's self-improving memory loop.
When Fritz operates on a 30-minute cron heartbeat (`heartbeat_wake`), it evaluates active state machine instances first. If a node is active in a workflow like `contribution.yaml`, Fritz inspects the node task, executes the code generation step using surgical replacements (`file_edit`), runs pytest verification gates, and advances the workflow state using `workflow_next`.
If a node failure occurs during step execution, calling `workflow_failure_record` increments the node retry counter. When the retry count hits `failure_limit=2`, Fritz auto-blocks the workflow instance, logs the failure reason, and triggers a cross-fleet alert via `speechops` TTS and `robofang` Council bridge. To resume execution after resolving the underlying issue, the operator invokes `workflow_unblock`.
To import third-party procedures into Fritz's procedural memory wiki, use the `import_external_skill` tool. Provide the path to any standard `SKILL.md` file (from OpenClaw, Anthropic skills, or Hermes Agent format). The tool parses the YAML frontmatter (`name`, `description`, `tags`) and Markdown content, creating a persistent skill card with `category=skill` and `created_by=import`.
