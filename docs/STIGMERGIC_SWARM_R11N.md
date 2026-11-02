# Stigmergic Swarm Architecture & r11n Specification — Action Plan

**Canonical Target**: `fleet-agent-mcp` (Fritz v0.3.0)  
**Date**: 2026-11-02  
**Status**: ACTIVE PROPOSAL / ROADMAP  
**Related Docs**: 
- `docs/AGENT_ARCHITECTURE_AND_SAFETY.md`
- `docs/coworker-plan.md`
- `SPEC.md`
- `mcp-central-docs/projects/fritz-coworker/STIGMERGIC_SWARM_R11N.md`
- Source inspiration: Google Drive design spec (`H:\My Drive\Stigmergic Swarm Architecture & r11n Specification.gdoc`)

---

## 1. Executive Summary

Fritz (`fleet-agent-mcp`, ports 10996/10997/11027) currently coordinates tasks via a **centralized, procedural state machine** (`flowforge`) executed on a cron heartbeat (`heartbeat_wake()`) and backed by a single SQLite database (`~/.fleet-agent/fleet-agent.db`).

While effective for isolated sequential flows, the comprehensive audit in `docs/AGENT_ARCHITECTURE_AND_SAFETY.md` and the 2026-09-08 VRAM stuck-loop incident revealed structural limits:
1. **Central Coordinator Bottleneck**: One hung workflow or exhausted LLM context blocks the entire execution queue.
2. **Procedural Fragility**: When a linear sequence (`study → implement → test → submit`) fails at any step, human intervention or complex rollback logic is required.
3. **Database Write Contention**: The single-writer SQLite constraint blocks true parallel worker execution across 200+ fleet repos.

This specification adopts a **Stigmergic Swarm Architecture with Reconciliation (`r11n`)**:
* **Stigmergic Coordination**: Autonomous agents coordinate *indirectly* by reading and modifying a shared environment (the filesystem, Git repos, health endpoints, and trace files), rather than relying on point-to-point RPC or a monolithic master coordinator.
* **Reconciliation Loop (`r11n`)**: Agents continuously observe actual environment state, compute the diff against declared desired invariants, execute localized remedial actions, prove verification mechanically, and update the environment trace.

---

## 2. Architectural Comparison

| Dimension | Current Architecture (Fritz v0.2.5) | Stigmergic `r11n` Swarm (Fritz v0.3.0) |
|---|---|---|
| **Coordination Model** | Centralized orchestrator (FlowForge DAG) | Decentralized stigmergy (Environment as Blackboard) |
| **Execution Trigger** | Periodic cron (`heartbeat_wake`) | State change sensors & threshold triggers |
| **State Storage** | Monolithic `fleet-agent.db` (single-writer) | Git + Filesystem substrate (`.r11n/`) + per-repo cache |
| **Execution Pattern** | Procedural sequence (`workflow_next(branch)`) | Declarative reconciliation (`Observe → Diff → Reconcile`) |
| **Failure Mode** | Hung node pins VRAM / halts queue | Lease expires (TTL); another worker resumes; anti-spin halts runaway |
| **Sub-Agent Reality** | In-process or one-shot RPC | Ephemeral task-scoped local workers with isolated contexts |
| **Scaling Capability** | 1 sequential pipeline | Multiple decoupled workers operating across fleet repos simultaneously |

---

## 3. Core Architectural Components

```
                   ┌──────────────────────────────────────────────┐
                   │           Shared Fleet Substrate             │
                   │  - Git Repos (code, commits, branches)       │
                   │  - Filesystem (.r11n/ traces, AGENTS.md)     │
                   │  - HTTP Endpoints (/api/health, ports)       │
                   └──────────────────────┬───────────────────────┘
                                          │
                 ┌────────────────────────┼────────────────────────┐
                 │                        │                        │
         [Senses Traces]          [Senses Traces]          [Senses Traces]
                 ▼                        ▼                        ▼
       ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
       │   Reconciler A   │     │   Reconciler B   │     │   Reconciler C   │
       │ (Contribution /  │     │ (Doc Drift &     │     │ (Service Health  │
       │    Bug Repair)   │     │    Standards)    │     │   & Watchdog)    │
       └────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
                │                        │                        │
         [Claims Lease &          [Claims Lease &          [Claims Lease &
          Alters State]            Alters State]            Alters State]
                │                        │                        │
                └────────────────────────┼────────────────────────┘
                                         ▼
                   ┌──────────────────────────────────────────────┐
                   │             Intel Reports Hub                │
                   │        Port 11027 Dashboard / State          │
                   └──────────────────────────────────────────────┘
```

### 3.1 The Shared Substrate (The Environment)
Rather than forcing all status into `fleet-agent.db`, the fleet itself is the primary memory substrate:
1. **Source Repos**: Test exit codes (`pytest`), lint output (`ruff`), uncommitted diffs.
2. **Metadata Files**: `AGENTS.md` (mandatory on 15+ files), `HANDOVER.md`, `fleet-start.config.ps1`.
3. **Pheromone Traces (`.r11n/`)**: Lightweight JSON trace files deposited in repos indicating status, work in progress, or needed attention.

### 3.2 The Trace & Lease Protocol
To prevent swarm collisions where two workers attempt to fix the same bug simultaneously:
* **Trace Directory**: `.r11n/` placed in target repos (ignored by git or tracked as status).
* **Claim File**: `.r11n/claim.json`
  ```json
  {
    "task_id": "r11n-fix-greeter",
    "worker_id": "fritz-worker-01",
    "claimed_at": 1793623000,
    "lease_ttl_seconds": 300,
    "status": "in_progress",
    "invariant": "pytest_green"
  }
  ```
* **Atomic Claiming**: Uses filesystem atomic operations (`os.O_CREAT | os.O_EXCL`) so only one worker secures the lease.
* **Orphan Recovery (TTL)**: If a worker crashes, `claimed_at + lease_ttl_seconds` expires; subsequent workers detect the stale claim and safely acquire it.

### 3.3 The Reconciliation (`r11n`) Loop
Every worker executes an invariant reconciliation loop:
1. **Observe**: Run diagnostic checks (e.g., `uv run pytest tests/`).
2. **Diff**: Compare observed outcome against the desired invariant (Expected: return code 0; Actual: return code 1, `NameError: grt undefined`).
3. **Reconcile**: Formulate targeted change, apply patch using safe file tools.
4. **Prove**: Re-run the diagnostic check. "Prove changes by running them" (Fleet Core Rule).
5. **Deposit Environmental Trace**: Commit change, post PR or update `HANDOVER.md`, release `.r11n/claim.json`.

### 3.4 Pheromone Evaporation & Anti-Spin Protection
Borrowing from biological stigmergy and Fritz's Hermes anti-spin system:
* **Failure Count**: If a worker fails 3 consecutive reconciliation cycles on the same target, it deposits a `.r11n/blocked.json` marker with `status: blocked`.
* **Evaporation**: Routine status traces expire after 24 hours without refresh to keep the environment uncluttered.
* **Escalation**: Blocked traces trigger an alert on the Intel Reports Hub (:11027) and notify the operator via AIWatcher/email.

---


### 3.5 Space-Efficient WSL2 Sandboxing Architecture (Anti-VM Strategy)

A core pitfall of multi-agent fleet operations is **VM storage and RAM exhaustion**. Spawning independent, full virtual machines (e.g. standard VirtualBox/VMware/KVM instances) per agent requires 15–30 GB per guest OS disk and locks 2–8 GB of static host RAM. Concurrently running 5–10 agents would quickly consume hundreds of gigabytes of SSD space and exhaust system memory on Goliath.

Instead, the Fritz r11n engine uses **WSL2 copy-on-write micro-sandboxing**:

1. **Shared Micro-Kernel & Dynamic Memory Reclaim**:
   - All agents share WSL2's single Hyper-V utility VM kernel, booting in <1 second.
   - Configured with `autoMemoryReclaim=gradual` in `%USERPROFILE%\.wslconfig`: as soon as an ephemeral worker finishes and exits, allocated memory is immediately returned to Windows.

2. **Sparse VHDX Auto-Compaction**:
   - Configured with `wsl --manage <distro> --set-sparse true`.
   - The virtual disk expands only when active bytes are written and automatically trims unused sectors back to the host NTFS file system upon task completion.

3. **OverlayFS (Shared Base + Ephemeral Upperdir)**:
   - System binaries, Python runtimes (`uv`), and Rust toolchains reside in a single shared, read-only base layer (`lowerdir`).
   - Each worker mounts a temporary scratch space (`upperdir`) in RAM (`tmpfs`) or a lightweight scratch folder.
   - Zero duplication of toolchains or dependencies across workers.

4. **Git Worktree Zero-Clone Isolation**:
   - Workers never clone full repositories (`git clone` duplicates object store and history).
   - Workers create an ephemeral worktree via `git worktree add /tmp/r11n-sandbox/<task_id> -b r11n/<task_id>`, taking <50ms and consuming only a few kilobytes.
   - Teardown is instant via `git worktree remove --force`.

5. **Rootless Ephemeral Namespaces**:
   - Process and network containment runs inside rootless Linux namespaces or lightweight Podman containers in WSL2, avoiding heavy Docker Desktop background overhead.

## 4. Action Plan & Phased Roadmap

### Phase 1: Substrate Primitives & Lease Engine (Sprint 1)
* [ ] Implement `src/fleet_agent/r11n/lease.py` in `fleet-agent-mcp`:
  * Atomic lease acquisition with TTL.
  * Stale lease recovery and heartbeat renewal.
  * Release and failure marking.
* [ ] Implement `src/fleet_agent/r11n/invariants.py`:
  * Standard invariant evaluators: `TestInvariant` (`pytest`), `LintInvariant` (`ruff`), `FileExistsInvariant` (`AGENTS.md`), `PortHealthInvariant` (`GET /api/health`).
* [ ] Add unit tests verifying concurrency safety and expiration behavior under `tests/test_r11n_lease.py`.

### Phase 2: Pilot 3 (`fritz-test`) Transformation (Sprint 2)
* [ ] Convert Pilot 3 (`fritz-test` bug target) from the linear `workflows/contribution.yaml` to the `r11n` engine.
* [ ] Verification run:
  1. Inject deliberate bug into `fritz-test/src/fritz_test/greeter.py`.
  2. Launch ephemeral Fritz worker (`uv run python -m fleet_agent.r11n.runner --target D:/Dev/repos/fritz-test`).
  3. Worker claims lease, detects failing `pytest`, isolates bug, applies fix, verifies `pytest` passes, creates PR, and cleans up lease.
* [ ] Document benchmark and token/cost comparison against old sequential pipeline.

### Phase 3: Fleet Doc-Drift & Standards Reconciler (Sprint 3)
* [ ] Create `DocDriftReconciler`:
  * Scans repos in `D:\Dev\repos\`.
  * Detects missing `AGENTS.md` for directories with 15+ files.
  * Validates hard rule compliance (absence of bash heredocs, valid port claims).
  * Automatically reconciles missing documentation headers and links.

### Phase 4: Swarm Supervision & Intel Reports Hub (Sprint 4)
* [ ] Extend Intel Reports Hub (port 11027) with a **Swarm Board**:
  * Live display of active `.r11n` claims across all fleet repos.
  * Visual indicators for healthy reconciliations vs blocked/escalated targets.
  * One-click manual lease revocation or trigger override.

---

## 5. Hard Fleet Rules Compliance Checklist

- [x] **No bash heredocs**: All file generation uses standard Write/Edit tools.
- [x] **No inline python string bugs**: All script invocations use dedicated file scripts.
- [x] **Ports claimed properly**: Reconciler uses assigned ports (backend 10996, webapp 10997, Intel Hub 11027); no hardcoded unassigned ports.
- [x] **Verification required**: Every reconciliation step must execute verification tests (`pytest`, `ruff`) before marking success.
- [x] **Backup discipline**: Existing files backed up with timestamped `.bak` before modification.
