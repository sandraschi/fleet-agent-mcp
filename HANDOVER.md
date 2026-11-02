# HANDOVER — fleet-agent-mcp (Fritz)

**As of:** 2026-11-02. **Version:** 0.3.0.

## What this repo is
Fritz: Self-evolving AI coworker, task orchestration, persistent memory, and fleet-wide stigmergic swarm reconciliation (`r11n`).

Ports: **10996** backend, **10997** webapp.

## Last concrete action (2026-11-02)
1. Built `src/fleet_agent/r11n/` stigmergic reconciliation core (leases, invariants, reconciler, background runner).
2. Exposed 4 FastMCP tools: `r11n_claim`, `r11n_status`, `r11n_release`, `r11n_check`.
3. Validated autonomous bug repair on `fritz-test` pilot fixture.
4. Documented WSL2 space-efficient micro-sandboxing tricks in `docs/STIGMERGIC_SWARM_R11N.md`.
5. Updated webapp dashboard and help pages with Stigmergic Swarm hero and documentation.
6. Tagged and released v0.3.0.
