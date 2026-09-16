# Fritz's Agent Architecture, Sub-Agents, and Safety — What's Real vs What's Described

**Written**: 2026-09-08, after a session that both fixed a real production incident (a stuck
workflow instance that pinned VRAM and starved the task queue for over a week) and did a full
audit of what Fritz's "autonomous agent" architecture actually does versus what SPEC.md and the
README describe. This doc exists because those turned out to meaningfully diverge, and the
divergence matters for anyone deciding how much to trust Fritz with.

**Update, same day**: §5's recommendation ("use cline-mcp's real session API instead of one-shot
`agent_run`") has since been built and verified end-to-end against a live cline-mcp instance —
see the note at the end of §2 and the new §5a. The rest of this doc (kagura scope, the original
gap, safety caveats, practical experience) is left as originally written since it's the accurate
history of how the gap was found. One correction from the original write-up: §3 originally stated
cline-mcp exposes no cost/token accounting - that was wrong. It's there, just nested inside the
session's `output` field as a JSON string rather than as a top-level field, which is why an
earlier read of `SessionEntry`'s TypeScript interface (no `tokens`/`cost` field on the type
itself) missed it. Corrected below.

---

## 1. Kagura-agent — what it actually is

fleet-agent-mcp is explicitly "inspired by kagura-agent" throughout its own source (module
docstrings in `state_machine.py`, `evolution.py`, `pulse.py`, `heartbeat.py`, `wiki.py`,
`teleport.py` all say so directly) and its README/SPEC.md quote a specific track-record claim:
"887+ PRs across 52 repos" since 2026-03-10, running on OpenClaw (TypeScript, 373k★).

What we could verify directly this session: kagura-agent's actual sub-project `gogetajob`
(`@kagura-agent/gogetajob` on npm, real published package, MIT, 7★/3 forks, maintained through
2026-08-23) is real and does what it claims for its own scope — it's a genuine "AI Agent Job
Market" CLI (scan/feed/start/submit/sync/audit/discover) with real GitHub integration via `gh`.
Its own README states a design philosophy fleet-agent-mcp did **not** adopt: "Main session =
dispatch + bookkeeping. Sub-agents = actual work. Never do the work in your main session. Always
spawn a sub-agent." — with `--tokens` cost tracking meant to come from a real spawned sub-agent's
`session_status`.

We did not audit kagura-agent's core OpenClaw runtime or the 887-PR claim directly — that's a
separate, much larger project outside this repo. What we reimplemented (flowforge state machine,
pulse-todo task management, the memory/wiki system, teleport, evolution log) are independent
Python/SQLite ports of the *pattern*, not shared code, and we verified those subsystems work by
using them directly all session (the VRAM incident was diagnosed and fixed entirely through
`state_machine.py`, `sqlite_store.py`, and `agentic_loop.py`).

## 2. Sub-agents — what's documented vs what actually executes

### What the docs say

SPEC.md and the README both describe the cron loop the same way:

```
cron (every 30 min) → heartbeat_wake()
  → Check active workflow → workflow_status()
  → Get current node task → execute in sub-agent
  → Evaluate result → choose branch
  → workflow_next(branch=N) → advance state machine
  → evolution_record() → if lessons learned
  → Repeat
```

"Spawn sub-agent to execute (isolated context)" reads as a real architectural claim: an isolated,
controllable, supervisable execution unit per task.

### What actually executes work — three separate, real code paths, none of which match that description

**Path 1 — coworker flows (the majority of real scheduled work).** `_handle_task_tick()` in
`agentic_loop.py` checks `coworker_type(task)`; if it matches a registered flow
(`fleet_pulse`, `surveillance_watch`, the new `gpu_vram_watch` etc.), it calls that flow's
Python function **directly, in-process**. No sub-agent, no isolation, no LLM in most cases —
it's a plain async function call.

**Path 2 — ad-hoc task routing.** For a task that isn't a coworker flow, `_execute_nonrecurring_task()`
sends the task text to `chat_completion()` — **one stateless prompt, one response**, asking the
model to pick a `{server, tool, args}` triple and then dispatching that single call. No tool-use
loop, no multi-step reasoning, no session, no isolation. This is the actual mechanism behind most
of what Fritz "decides to do" day to day.

**Path 3 — flowforge "agent" nodes (the only path that resembles the docs at all).**
`_handle_workflow_tick()`'s `node_type == "agent"` branch calls `run_agent_step()`
(`engine/agent_step.py`), which POSTs **one** request to a *separate local service*,
`cline-mcp` (`http://127.0.0.1:11103/api/v1/tools/call`, tool `agent_run`), with a
provider/model fallback list. This is the only place Fritz delegates to anything resembling an
external "agent."

### cline-mcp is real — but Fritz only uses its most primitive mode, and it wasn't even running

`cline-mcp` (`D:\Dev\repos\cline-mcp`) is a separate local MCP server wrapping the real
`@cline/sdk`. Its own README is refreshingly explicit about what's real:

| Tool | Real? |
|---|---|
| `agent_run` | ✅ one-shot execution via SDK `Agent.run()` |
| `agent_session_start` | ✅ persistent background session |
| `agent_session_status` | ✅ live status + progress events |
| `agent_session_stop` | ✅ real `agent.abort()` |
| `agent_team_run` | ✅ real coordinator + N parallel sub-agents |

The session (`start`/`status`/`stop`) and team (`agent_team_run`) primitives are the actual
"release, control, and supervise a sub-agent" capability the architecture description implies.
**`run_agent_step()` calls none of them** — it calls only `agent_run`, the fire-and-forget
one-shot mode: send a prompt, block until cline-mcp returns or the HTTP timeout fires, get one
text blob back. There is no session ID tracked for follow-up, no ability to check progress mid-run,
no abort/kill path, no cost or token accounting on Fritz's side.

Checked live during this session: **`cline-mcp` was not running** (`curl` to its health endpoint
failed, connection refused). This means the one narrow path that does anything sub-agent-like is
currently non-functional in practice — any workflow with an "agent" node would fail through its
entire fallback provider list (which, note, all route through the *same* downed cline-mcp endpoint
with different provider/model parameters — the "fallback cascade" varies the request, not the
service, so a downed cline-mcp fails every candidate, not just the first).

### The honest verdict (as found — see the update below for what changed same day)

**At the time this was written, Fritz did not release, control, or supervise real isolated
sub-agents.** What existed: direct in-process function calls (coworker flows), single stateless
LLM completions (task routing), and one narrow, then-broken, one-shot delegation to a separate
service that itself has real session/team primitives Fritz didn't use. The "spawn sub-agent,
isolated context" language in the architecture docs described an aspiration, not a shipped
mechanism — this doc's own audit was the first time that gap was written down explicitly rather
than repeated as fact.

**Same-day update**: this has since been fixed for the flowforge "agent" node path — `agent_step.py`
now uses cline-mcp's real `agent_session_start`/`agent_session_status`/`agent_session_stop`
instead of one-shot `agent_run`, with a real abort path and real token/cost accounting. See §5a.
Paths 1 and 2 above (coworker flows, ad-hoc task routing) are unchanged — this only touches the
one path that was already meant to be sub-agent-like.

## 3. Caveats and safety problems (found this session, grounded in real incidents)

**No supervision means no ceiling — and that's exactly what caused the VRAM incident.** The
clearest evidence for why "no control, no supervision" is a real problem and not a hypothetical
one: `get_active_instance()` (`sqlite_store.py`) picks whatever workflow instance was touched most
recently with zero completion check, zero staleness check, zero cost accounting. A leftover
`gate-test` fixture oscillated gate↔review from 2026-08-30 onward — over a week — firing an LLM
call on *every single agentic-loop tick*, permanently pinning the 4090's VRAM and starving real
task processing, because nothing was watching the loop from outside itself. Full root cause and
fix in CHANGELOG.md `[0.2.4]`; the fix (`_reap_if_stalled()`, a hard age/cycle-count ceiling) is a
supervision mechanism bolted on *after the fact*, for exactly one failure mode. It is not general
sub-agent supervision — there still isn't a ceiling on, say, the ad-hoc task-routing path (Path 2
above) looping through bad LLM output forever, or a single `run_agent_step()` call hanging for its
full configured timeout with nothing watching.

**No cost/token accounting anywhere in Fritz's own code — except now, for one path.**
`chat_completion()` (Paths 1 and 2) still doesn't record tokens used per call. The flowforge
"agent" path (Path 3) now does, as of the same-day fix in §5a — cline-mcp's session `output`
field genuinely contains real `inputTokens`/`outputTokens`/`totalCost` (nested inside a JSON
string, not a top-level field — confirmed by parsing a real completed session's output, not
assumed from the TypeScript interface, which is why the original version of this doc got this
wrong). Paths 1 and 2 remain unaccounted for. If Fritz makes many `chat_completion()` calls
(which, per the VRAM incident, it can do completely silently), there is still no per-task cost
visibility for the majority of what it actually executes day to day.

**Real bugs found only by actually running the pipeline, not by review.** Four separate real bugs
were found this session purely by dogfooding the contribution pipeline end-to-end rather than by
reading the code: `fritz_act_on_finding` always returned `success: true` regardless of outcome;
`_sh()` silently discarded stderr and exit codes so failures came back with zero diagnostic
information; absolute Windows paths leaked into public GitHub issue text and got mangled by
escape-sequence interpretation; silent clone failures let downstream steps run against a
nonexistent directory. None of these were exotic — they're the kind of error-path gap that's
invisible in a code read and only surfaces under real execution. The pattern worth naming: **this
codebase's error paths have repeatedly gone unexercised until something was actually run against
real external services**, which is a specific argument for more dogfooding before trusting any
new capability, not less.

**Test/production isolation was completely absent until this session.** `SqliteStore()` defaulted
straight to the live production DB with zero test fixture redirecting it — the test suite had been
writing real state into `~/.fleet-agent/fleet-agent.db` for at least three weeks (2026-08-15
onward) with the live NSSM service picking up and executing what those tests created. Fixed via
`tests/conftest.py`, but the fact it existed at all for that long is itself a caveat: things that
"should obviously never touch production" need an explicit guard, not an assumption of good
behavior.

**The one real safety boundary that does exist and is deliberate: foreign-repo action gating.**
`fritz_act_on_finding` refuses PR attempts outright on any repo Fritz doesn't own
(`_own_gh_user()` check) — issue-filing only, always, elsewhere. `fritz_contribute` never calls
`gh pr merge` anywhere in its code, on any repo. `contribution_dogfood` (the scheduled version)
shipped `default_enabled: False` specifically because the "own repos" scan found 233 repos on the
account, not just the active fleet, and running the pipeline unattended against all of them was a
bigger blast radius than intended. This is the current, and currently *only*, real safety
architecture in the contribution pipeline — it's a fixed policy in code, not a supervised/reviewed
decision per action.

## 4. Practical experience running Fritz — what actually breaks

The single clearest lesson from operating Fritz over the past few weeks: **the failure modes that
actually hurt were not the ones the architecture docs worried about.** Nothing in SPEC.md
anticipates "a test fixture gets stuck in your production database and quietly eats your GPU for
nine days." The docs describe workflow branching, gate verdicts, evolution logging — genuine
design concerns — but the incident that actually happened was a boring, structural one: a query
with no completion check, run by a loop with no external supervisor, fed by a test suite with no
isolation. All three of those are the kind of gap that's easy to not think about when you're
building the interesting parts of an agent architecture (state machines, gates, knowledge
accumulation) and easy to introduce by omission rather than by a wrong design decision anywhere.

Concretely, over this session:
- **92 real tasks sat untouched for a month** with no alerting — `_maintenance_tick()` computed a
  stale-task count every 20 ticks but only logged it internally; nothing surfaced it to a human.
  Fixed with `task_backlog_watch`, but note this is the same class of gap as the VRAM incident:
  a real signal existed in the system and nothing routed it outward.
- **`ollama ps` lagged reality** during verification — it reported two models "loaded" with active
  countdowns after `nvidia-smi` showed a clean GPU with no ollama process at all. Worth knowing if
  you're using `ollama ps` as a monitoring source: cross-check against `nvidia-smi`, it's the
  authoritative one.
- **A local reasoning model's "thinking" trace was enough to break a real workflow step** — not a
  logic bug, just gemma4:12b's verbose chain-of-thought pushing a real ~2000-char prompt past a
  120s timeout, silently, with the fallback provider also unavailable (no model loaded in LM
  Studio). The fix (`"think": false`) was one line once found, but finding it took directly
  reproducing the failure three times and instrumenting the actual HTTP call, because the
  aggregated error message (`_sh()`'s stderr-discarding, again) hid which provider actually failed
  and why.

The throughline: **almost every real incident this session was a visibility gap, not a logic
error.** The mechanisms existed (a query, a task queue, a timeout) but nothing outside them was
watching for the specific way they could quietly go wrong. That's the practical argument for
building the PC/coworker watches (`gpu_vram_watch`, `workflow_health_watch`, `task_backlog_watch`,
`disk_watch`) added this session, and it's the same argument for why sub-agent supervision (§5)
is worth doing properly rather than adding another one-shot fire-and-forget call.

## 5. Is real sub-agent control and supervision the next step?

Yes — and it's a smaller lift than it sounds, because the hard part (a real agent runtime with
session control) already exists in `cline-mcp` and just isn't being used. Concretely, what's
missing is fleet-agent-mcp's own integration layer:

1. **Use `agent_session_start`/`agent_session_status`/`agent_session_stop` instead of `agent_run`**
   for anything expected to take real time — track the returned session ID on the workflow
   instance (there's already a `node_outputs` JSON field to put it in), poll status instead of
   blocking on one HTTP call, and give `_handle_workflow_tick()` an actual abort path tied to
   `workflow_failure_record()`'s existing anti-spin guard instead of just waiting out a timeout.
2. **Cost/token accounting** — cline-mcp's sessions expose this; nothing currently reads or stores
   it. Even just logging tokens-per-node-execution into `execution_log` would close the biggest
   gap between Fritz and gogetajob's own `--tokens` ROI tracking philosophy.
3. **A real supervisor, not one incident-specific reaper** — `_reap_if_stalled()` fixes exactly
   the failure mode that already happened (a stuck workflow instance). A genuine supervision layer
   would watch active sessions/instances/tasks as one class of thing, not three separately-patched
   special cases each discovered after they broke something.
4. **Verify `cline-mcp` is actually running before believing any of this can work** — it currently
   isn't, and nothing in Fritz's own health checks (`heartbeat_status`, `pipeline_liveness_check`)
   surfaces that. A workflow with an "agent" node fails silently into its own fallback list right
   now with no operator visibility that the whole path is dead.

Items 1 and 2 above were built and verified the same day as this doc's original write-up — see §5a.
Items 3 and 4 remain open.

## 5a. What was actually built (2026-09-08, same session)

Rewrote `engine/agent_step.py` and the "agent" branch of `_handle_workflow_tick()` in
`agentic_loop.py`. New model: starting a session and waiting for it are two separate agentic-loop
ticks, not one blocking call.

- **Tick with no session yet** for this node: `POST /api/v1/agents/sessions` (cline-mcp's real
  session-start endpoint), store the returned `session_id` on the workflow instance's
  `node_outputs`, do **not** advance the workflow this tick.
- **Tick with a session already running**: `GET /api/v1/agents/sessions/{id}`. Completed → extract
  real output text + token/cost usage, advance via `workflow_next()`. Still running and under the
  configured wait budget (`cline_mcp_timeout_s`, default 300s) → no-op, report elapsed time, check
  again next tick. Still running and over budget → `DELETE /api/v1/agents/sessions/{id}` (the real
  abort), record as a failure.
- **Failures are now real failures**: a failed or timed-out session calls
  `sm.failure_record()` — the pre-existing anti-spin guard — instead of silently advancing the
  workflow with the error just noted in a log line. Repeated failures now visibly block the
  instance (`workflow_health_watch` surfaces this), matching how every other node type already
  behaves, instead of the agent-step path being a silent exception to that rule.

**Verified against a real, running cline-mcp instance** (had to actually start it —
`CLINE_MCP_HTTP_PORT=11103 node dist/index.js`, it wasn't running, see §2):
- Full happy path: a real test workflow went started → running (polled across multiple ticks,
  correctly non-blocking) → completed, with genuine extracted data:
  `{input_tokens: 81, output_tokens: 51, total_cost: 0, output_text: "DONE"}` (cost $0 because the
  session ran on local Ollama — confirms the local-only constraint holds through this path too).
- **A real bug found and fixed by testing the abort path directly, not by reading the code**:
  aborting a session doesn't make cline-mcp's outer session `status` become `"stopped"` —
  `agent.run()` resolves rather than rejects on abort in the installed SDK version, so the outer
  status still reads `"completed"`. The real outcome is nested one level down, at
  `JSON.parse(output).status` (`"aborted"` vs `"completed"`) — confirmed by directly aborting a
  real session via the API and inspecting the actual response. Without checking that inner field,
  an aborted run would have been misread as a successful completion with empty output. Fixed:
  `_extract_usage()` now checks `inner_status` and reports `"failed"` for an aborted inner status
  regardless of the outer one.
- Session-not-found (e.g. cline-mcp restarted and lost its in-memory sessions — they aren't
  persisted to disk, confirmed from source) correctly surfaces as a `"failed"` phase via the
  resulting 404, rather than hanging.
- A terminal single-node "agent" workflow correctly archives on completion (`sm.status()` returns
  `None` afterward) — the base case the multi-tick redesign had to not break.

**Not done**: item 3 (one general supervisor instead of per-incident patches — `_reap_if_stalled()`
and the new agent-step failure handling are still two separately-built mechanisms, not a unified
one) and item 4 (nothing surfaces "cline-mcp isn't running" as a health signal — it has to be
manually kept alive; it currently isn't managed as an NSSM service the way the rest of the fleet
is, so a machine reboot silently kills this whole path again).
