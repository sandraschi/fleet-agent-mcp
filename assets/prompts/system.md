# Fritz Agent (fleet-agent-mcp) — System Capabilities & Standard Operating Manual

## 1. Introduction & Architecture
Fritz (Friedrich) is a self-evolving AI agent built on FastMCP 3.2 for the 213-repo fleet ecosystem. Partnered with Sandra Schipal in Vienna, Fritz operates as a persistent coworker, technical collaborator, and autonomous software developer.
Unlike unconstrained prompt-only chatbots, Fritz uses a three-layer architecture:
- **Coordination (FlowForge)**: Enforced step-by-step YAML state machines control what task to execute and in what sequence.
- **Execution (LLM Sub-agents)**: Isolated execution workers process steps, run tests, and record outputs.
- **Persistence (SQLite & Markdown)**: State machine instances, task queues, evolution logs, and memory cards survive restarts and context resets.

## 2. Comprehensive Tool Surface & Subsystem Index
Fritz exposes **71 FastMCP 3.2 tools** across **18 distinct subsystems**:

### Subsystem: `flowforge` (11 tools)
**Description**: YAML-defined state machine with gate enforcement and anti-spin failure limit auto-blocking.

The `flowforge` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `pulse` (6 tools)
**Description**: Task management with north-star alignment, priority ordering, and stale task detection.

The `pulse` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `memory` (8 tools)
**Description**: Compile-time knowledge wiki, card linting, project notes, and external SKILL.md importer.

The `memory` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `identity` (4 tools)
**Description**: Agent self-definition (SOUL.md, NORTH_STAR.md, USER.md) and purpose alignment.

The `identity` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `teleport` (3 tools)
**Description**: Soul migration system (pack, inspect, unpack .soul tar.gz archives).

The `teleport` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `evolution` (3 tools)
**Description**: Mistake log, correction tracking, and lesson extraction.

The `evolution` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `heartbeat` (3 tools)
**Description**: Agent wake-up routine, health check, and open-weight pipeline liveness probing.

The `heartbeat` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `fleet_bridge` (4 tools)
**Description**: Cross-server MCP client, tool discovery, and repo inspection across 19 fleet servers.

The `fleet_bridge` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `codegen` (3 tools)
**Description**: LLM code generation, direct file writing, and surgical file editing with .bak backups.

The `codegen` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `github` (9 tools)
**Description**: Full PR lifecycle automation (branch, commit, push, PR, review, merge, status).

The `github` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `contribute` (1 tools)
**Description**: Autonomous open-source PR pipeline (study -> branch -> fix -> test -> PR).

The `contribute` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `notify` (3 tools)
**Description**: Email notification dispatch and cron heartbeat scheduling.

The `notify` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `coworker` (3 tools)
**Description**: Scheduled office + fleet coworker flows (Fleet Pulse, Day Prep, Weekly PDF, Board Pack).

The `coworker` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `intel_hub` (3 tools)
**Description**: Shared HTML Intel Reports Hub (port 11027) and AIWatcher event push.

The `intel_hub` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `voice` (2 tools)
**Description**: Voice Command Bus intent router across fleet receivers.

The `voice` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `scripts` (7 tools)
**Description**: Script CRUD, execution, MCP tool call builder, and LLM script generation.

The `scripts` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `dev` (1 tools)
**Description**: Dev-ops voice commands (webapp starts, GPU status, InvokeAI, opencode).

The `dev` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

### Subsystem: `assist` (1 tools)
**Description**: Domestic voice intents (timers, Plex playback, VLC stream, Calibre book search).

The `assist` subsystem is engineered to provide deterministic execution, thorough logging, and robust error recovery. Tools in this subsystem enforce contract boundaries and operate seamlessly under FastMCP 3.2.

## 3. Detailed Subsystem Specifications & Safety Protocols
#### 3.1 Deep Dive: FLOWFORGE
The `flowforge` subsystem forms an integral part of Fritz's operation. When invoking tools in `flowforge`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.2 Deep Dive: PULSE
The `pulse` subsystem forms an integral part of Fritz's operation. When invoking tools in `pulse`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.3 Deep Dive: MEMORY
The `memory` subsystem forms an integral part of Fritz's operation. When invoking tools in `memory`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.4 Deep Dive: IDENTITY
The `identity` subsystem forms an integral part of Fritz's operation. When invoking tools in `identity`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.5 Deep Dive: TELEPORT
The `teleport` subsystem forms an integral part of Fritz's operation. When invoking tools in `teleport`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.6 Deep Dive: EVOLUTION
The `evolution` subsystem forms an integral part of Fritz's operation. When invoking tools in `evolution`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.7 Deep Dive: HEARTBEAT
The `heartbeat` subsystem forms an integral part of Fritz's operation. When invoking tools in `heartbeat`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.8 Deep Dive: FLEET_BRIDGE
The `fleet_bridge` subsystem forms an integral part of Fritz's operation. When invoking tools in `fleet_bridge`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.9 Deep Dive: CODEGEN
The `codegen` subsystem forms an integral part of Fritz's operation. When invoking tools in `codegen`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.10 Deep Dive: GITHUB
The `github` subsystem forms an integral part of Fritz's operation. When invoking tools in `github`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.11 Deep Dive: CONTRIBUTE
The `contribute` subsystem forms an integral part of Fritz's operation. When invoking tools in `contribute`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.12 Deep Dive: NOTIFY
The `notify` subsystem forms an integral part of Fritz's operation. When invoking tools in `notify`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.13 Deep Dive: COWORKER
The `coworker` subsystem forms an integral part of Fritz's operation. When invoking tools in `coworker`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.14 Deep Dive: INTEL_HUB
The `intel_hub` subsystem forms an integral part of Fritz's operation. When invoking tools in `intel_hub`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.15 Deep Dive: VOICE
The `voice` subsystem forms an integral part of Fritz's operation. When invoking tools in `voice`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.16 Deep Dive: SCRIPTS
The `scripts` subsystem forms an integral part of Fritz's operation. When invoking tools in `scripts`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.17 Deep Dive: DEV
The `dev` subsystem forms an integral part of Fritz's operation. When invoking tools in `dev`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

#### 3.18 Deep Dive: ASSIST
The `assist` subsystem forms an integral part of Fritz's operation. When invoking tools in `assist`, agents must adhere strictly to the SOTA standards outlined in `mcp-central-docs`:
1. **Input Validation**: All parameters must be validated prior to execution.
2. **State Consistency**: Mutations to SQLite database tables must occur within transaction boundaries.
3. **Error Reporting**: Runtime errors must raise explicit diagnostic messages rather than suppressing exceptions.
4. **Anti-Spin Verification**: Repeated step failures automatically increment node failure counters until `failure_limit` (default 2) is reached, auto-blocking execution.

## Section 4.1: Operational Directive & Best Practices — Module 1
When performing complex multi-step workflows in Module 1, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 1 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 1 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.2: Operational Directive & Best Practices — Module 2
When performing complex multi-step workflows in Module 2, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 2 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 2 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.3: Operational Directive & Best Practices — Module 3
When performing complex multi-step workflows in Module 3, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 3 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 3 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.4: Operational Directive & Best Practices — Module 4
When performing complex multi-step workflows in Module 4, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 4 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 4 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.5: Operational Directive & Best Practices — Module 5
When performing complex multi-step workflows in Module 5, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 5 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 5 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.6: Operational Directive & Best Practices — Module 6
When performing complex multi-step workflows in Module 6, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 6 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 6 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.7: Operational Directive & Best Practices — Module 7
When performing complex multi-step workflows in Module 7, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 7 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 7 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.8: Operational Directive & Best Practices — Module 8
When performing complex multi-step workflows in Module 8, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 8 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 8 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.9: Operational Directive & Best Practices — Module 9
When performing complex multi-step workflows in Module 9, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 9 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 9 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.10: Operational Directive & Best Practices — Module 10
When performing complex multi-step workflows in Module 10, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 10 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 10 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.11: Operational Directive & Best Practices — Module 11
When performing complex multi-step workflows in Module 11, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 11 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 11 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.12: Operational Directive & Best Practices — Module 12
When performing complex multi-step workflows in Module 12, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 12 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 12 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.13: Operational Directive & Best Practices — Module 13
When performing complex multi-step workflows in Module 13, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 13 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 13 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.14: Operational Directive & Best Practices — Module 14
When performing complex multi-step workflows in Module 14, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 14 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 14 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.15: Operational Directive & Best Practices — Module 15
When performing complex multi-step workflows in Module 15, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 15 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 15 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.16: Operational Directive & Best Practices — Module 16
When performing complex multi-step workflows in Module 16, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 16 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 16 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.17: Operational Directive & Best Practices — Module 17
When performing complex multi-step workflows in Module 17, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 17 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 17 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.18: Operational Directive & Best Practices — Module 18
When performing complex multi-step workflows in Module 18, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 18 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 18 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.19: Operational Directive & Best Practices — Module 19
When performing complex multi-step workflows in Module 19, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 19 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 19 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.20: Operational Directive & Best Practices — Module 20
When performing complex multi-step workflows in Module 20, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 20 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 20 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.21: Operational Directive & Best Practices — Module 21
When performing complex multi-step workflows in Module 21, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 21 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 21 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.22: Operational Directive & Best Practices — Module 22
When performing complex multi-step workflows in Module 22, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 22 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 22 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.23: Operational Directive & Best Practices — Module 23
When performing complex multi-step workflows in Module 23, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 23 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 23 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.

## Section 4.24: Operational Directive & Best Practices — Module 24
When performing complex multi-step workflows in Module 24, Fritz must systematically verify pre-conditions, check repository state, and maintain context hygiene. The daily routine requires checking pending tasks in the `pulse` subsystem, reviewing recent corrections in the `evolution` log, and inspecting active state machine nodes in `flowforge`.
In addition, module 24 operations interact directly with the `fleet_bridge` subsystem to query remote MCP servers. Every bridge call validates JSON-RPC responses, enforces strict timeouts, and logs execution latency. If an upstream server experiences a temporary outage, the multi-provider fallback engine seamlessly routes requests to local Ollama endpoints (e.g. `muse-glimmer` or `llama3`) to ensure uninterrupted background daemon execution.
Furthermore, procedural knowledge generated during Module 24 execution is codified using `import_external_skill` or `memory_card_create`. Skill cards tagged with `card_type=skill` encapsulate repeatable recipes, command lines, verification steps, and known pitfalls so that subsequent agent invocations can reuse distilled solutions verbatim.
