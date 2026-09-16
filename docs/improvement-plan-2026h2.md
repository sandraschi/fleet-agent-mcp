# Fritz Improvement Plan 2026H2

Status: PLAN (nothing below is implemented unless marked VERIFIED)
Created: 2026-08-29, after the SFB surveillance audit and 0.2.3 hardening
Scope: fleet-agent-mcp (Fritz) and its immediate collaborators (discord-mcp, cline-mcp, mcp-federation-hub, admiral-mcp)

## 1. Ground truth (VERIFIED, 2026-08-29)

- Fritz runs 69 tools, 15 subsystems: state machine + mechanical gates, coworker flows, intel hub (11027), memory wiki, identity/soul, heartbeat, teleport, fleet bridge (20 servers), SFB comms layer.
- 0.2.3 shipped: [agent] attribution on Discord, involuntary harness lifecycle posting (start/completed -> #sfb-work, BLOCKED -> #sfb-alerts).
- Known weaknesses seen in code and logs this session:
  - agentic_loop gate nodes DEFAULT TO PASS when the LLM verdict call fails or returns garbage. A dead brain tier waves everything through. This inverts the whole mechanical-gate philosophy.
  - The LLM task router prompt hardcodes 6 servers; fleet_bridge knows 20.
  - fleet-hub restarts roughly every 20 minutes (900+ rotated log pairs in logs/ since 2026-08-20). Cause unknown.
  - Daily fleet pulse has said DEGRADED, 8-10/29 MCP online, 1 critical alert since at least 08-26 with no escalation.
  - sfb_budget.json lives in Path.home() (LocalSystem trap); work-budget keys never expire; sanitizer redacts 40-hex commit SHAs.

## 2. Principles (unchanged, research-confirmed)

- Board/diary is source of truth; Discord is a sanitized mirror. Keep it that way.
- Guardrails live in the runtime, not the prompt. Current harness engineering consensus: the model is never the only enforcement layer; destructive tools, secrets, network egress and external writes need runtime policy. Fritz's gate_engine is the right foundation.
- The agent that builds never evaluates (OPC). Extend, never dilute.
- Budget: ~100 EUR/month total AI spend. MCP sampling against Claude Desktop Pro stays the trick for hard reasoning at zero marginal cost; local models take volume work.
- Rules that must survive belong in SOUL.md / system prompt, never in compactable history. (Claude Code compaction analysis: initial instructions and style rules are exactly what compaction loses.)

## 3. Workstreams

### A. Gate integrity (highest priority, ~1 day)
1. Fail-closed gates: LLM failure or invalid verdict -> ITERATE (and failure_record), never PASS. One conditional in agentic_loop, plus test.
2. Rubric verdicts instead of one-word verdicts: gate nodes carry a small rubric (from criteria_text) and the judge must fill it; gate_engine synthesizes the verdict mechanically from the filled rubric. Research: test-time rubric-guided verification is the 2026 pattern for self-evolving research agents; it fits gate_engine's deterministic synthesis exactly.
3. Router honesty: generate the router tool list from fleet_bridge's live registry instead of the hardcoded 6-server prompt.

### B. Skills as memory (the big one, ~3-4 days)
Fritz already has the pieces (memory wiki cards, evolution log, import_external_skill, SKILL.md compatibility). 2026 research converged on skills-as-evolving-memory: Memento-Skills (agents improving via structured markdown skill repositories, parameter-free continual learning), MemSkill (controller selects skills, designer periodically reviews failures and evolves the skill set), SkillOS (skill curation), Recuris (experiential vs working memory split for long-horizon harnesses; already flagged in #sfb-alerts 08-26).
1. Skill distillation flow: nightly coworker flow reads the evolution log + diary repo_fix/blooper entries, drafts candidate SKILL.md cards, posts them to #sfb-thoughts and a hub board queue. Human approves; approved skills land in the wiki and are injected into matching agent steps.
2. Working/experiential split (Recuris pattern): agent steps get (a) working memory = current instance node_outputs (exists) and (b) a small retrieved set of approved skills, not the whole wiki.
3. Skill lifecycle: every skill card carries hit/miss counters (did the step citing it pass its gate); a monthly designer pass proposes retire/refine, gated by human approval. No autonomous self-modification of skills.

### C. Context engineering for agent steps (~2 days)
1. Artifact offloading: big outputs (logs, reports, diffs) go to the intel hub with a handle; agent step prompts carry handles + summaries, never raw dumps. (Prime Agent L1/L3 layering; compaction research: context rot degrades accuracy 14-85 percent well before the window fills.)
2. Compaction discipline: compaction for coworker/agent contexts is boundary-aware (never mid-subgoal) and provenance-preserving; hard rules never enter the compactable region.
3. Subagents only for context isolation or parallel exploration, not for architecture theater. Fritz stays a single agent with scoped steps until a concrete need appears.

### D. Security: injection and tool poisoning (~2 days)
Threat picture 2026: indirect prompt injection via tool results is demonstrated against production agents (GitHub PR-title hijack of Claude Code / Gemini CLI / Copilot, April 2026); tool poisoning via metadata is OWASP-catalogued; the trust gap is connect-time review vs unchecked runtime responses. Practical consensus: fix governance gaps (audit, identity, tool ACLs) before chasing perfect injection defense.
1. UNTRUSTED wrapping everywhere Fritz ingests external content: email bodies, arxiv abstracts, scraped pages, Discord reads. discord-mcp already does it; make it a fleet_bridge-level convention with a shared wrapper.
2. Per-node tool allowlists: workflow YAML gains an optional tools: list per node; fleet_call_tool enforces it in the runtime. Injected instructions cannot call tools the node never had.
3. Verify-before-commit for side-effectful bridge calls (VIGIL pattern): plans that include external writes (email send, Discord post outside SFB, file deletes) are checked against the node's declared intent before execution; mismatch -> BLOCKED + admiral inbox.
4. Tool metadata pinning: fleet_bridge hashes tool descriptions at connect time; changed descriptions raise an alert before use (counters rug-pull tool poisoning).
5. SFB backlog from the 08-29 audit: split bot tokens (send-only for agents) or drop Manage Channels; surveil rule diffing live guild channels vs sanctioned map; surveil rule grepping agent-written code for discord.com/api, webhook URLs, unexpected ports; daily discord_error reconciliation post.

### E. Brain tier and economy (~2-3 days, partly blocked on hardware reality)
1. ds4 evaluation on Goliath: DwarfStar (antirez) runs DeepSeek V4 Flash locally via asymmetric 2-bit quant, CUDA supported, SSD streaming for smaller-RAM machines, DSpark speculative decoding opt-in. HYPOTHESIS: acceptable tokens/s on a 4090 + system RAM + NVMe streaming; benchmark before committing. If viable, ds4 HTTP API becomes a cline-mcp provider next to ollama.
2. Tiered routing by node type: gates and routing on the cheapest adequate local model; agent (SFB brain) steps on the best local; anything failing twice escalates to MCP sampling (Claude, zero marginal cost) with the failure context attached.
3. Token/cost accounting per flow in the diary metrics, so the monthly budget check is a query, not a feeling.

### F. Reliability and ops (~1-2 days)
1. Diagnose the fleet-hub 20-minute restart loop (NSSM throttle? crash? scheduled?). 900 log pairs is not a log rotation policy, it is a symptom.
2. Log hygiene: cap rotated logs (NSSM AppRotateBytes/AppRotateOnline or a daily sweep flow), current logs/ dir is ~2 weeks from being a disk problem.
3. Escalation policy: same critical pulse alert N consecutive days -> urgent admiral inbox + louder SFB alert. Alert fatigue is the current state.
4. NSSM env-pinning audit for every service touching Path.home() (known LocalSystem systemprofile trap); move sfb_budget.json to data_dir regardless.
5. Budget key expiry (work keys older than 7 days pruned on load).

### G. Human loop (~1 day)
1. Gate overrides and BLOCKED unblocks approvable from Admiral Pager (admiral-mcp inbox already exists as the urgent path).
2. Weekly surveillance digest: one #sfb-alerts post summarizing agent activity, budget spend, skills approved/retired, security events. Human-readable, five lines.

## 4. Sequencing (AI-assisted, days not weeks)

- Phase 1 (1-2 days): A complete, F1-F3. Fail-closed gates and the restart loop are the two things most likely to be silently hurting right now.
- Phase 2 (2-3 days): D1-D4 security runtime, D5 SFB backlog.
- Phase 3 (3-4 days): B skills-as-memory loop, C context engineering.
- Phase 4 (2-3 days): E brain tier after a ds4 benchmark day, G human loop polish.

Total: roughly two working weeks of sessions, each phase independently shippable with its own gates.

## 5. Non-goals (deliberate)

- No RL / weight training of anything. Skill evolution stays parameter-free markdown (Memento-Skills showed this is enough for large gains).
- No autonomous self-modification: every skill add/retire, gate rubric change, and security policy change passes a human approval, posted where you can read it.
- No new agent-to-agent protocols (A2A etc.) until a second real agent exists that needs one.
- No Discord as transport. Mirror only, forever.

## References (retrieved 2026-08-29)

- MemSkill, arXiv 2602.02474; Memento-Skills, arXiv 2603.18743; SkillOS, arXiv 2605.06614; Recuris, arXiv 2608.24876
- Self-Compacting LM Agents, arXiv 2606.23525; Slipstream, arXiv 2605.08580; Prime Agent, arXiv 2608.23552
- OWASP MCP Tool Poisoning; Aptible MCP prompt injection / blast radius guide; VIGIL, arXiv 2601.05755
- Modern Agent Harness Blueprint 2026 (gist, amazingvince); awesome-harness-engineering
- DwarfStar ds4, github.com/antirez/ds4, dwarfstar.sh
