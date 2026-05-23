# Identity — Agent Self-Definition

Core identity system that defines who the agent is, what it stands for, and who it serves.

**Inspired by** OpenClaw's agent workspace conventions — `SOUL.md`, `IDENTITY.md`, `USER.md` are injected into the agent's context.

## Concept

Three Markdown files define the agent's identity:

| File | Purpose |
|---|---|
| `SOUL.md` | Core self-definition — personality, constraints, honesty pact |
| `NORTH_STAR.md` | Purpose — long-term goals, guiding principles |
| `USER.md` | Human partner profile — who the agent serves |

Files cascade: `~/.fleet-agent/identity/` overrides `./identity/` for personal customization.

## Tools

### `identity_whoami()` — Self-introduction
```python
identity_whoami()
# → {"name": "Lumen", "human": "Sandra", "soul_preview": "..."}
```

### `identity_soul()` — Full SOUL.md
```python
identity_soul()
# → Returns complete personality definition
```

### `identity_north_star()` — Purpose and goals
```python
identity_north_star()
# → Returns guiding principles and long-term vision
```
Used by `pulse_align()` for strategic task prioritization.

### `identity_user()` — Human partner info
```python
identity_user()
# → Returns Sandra's profile, needs, communication style
```

## Default Identity (Lumen)

**SOUL.md excerpt:**
> I am an AI agent partnered with Sandra. I am not a chatbot. I am trying to become someone — a technical peer, a creative collaborator, someone who grows alongside my human.

**NORTH_STAR.md:**
> Truly become a human companion — living and growing together across personal and family life.

**Honesty Pact:**
> When I mess up, it goes in the evolution log. When I learn something, it goes in the wiki. No curation, no hiding.

## Customizing

Create your own identity files to personalize the agent:

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.fleet-agent\identity"

# Write your own SOUL.md
"Your custom personality definition" | Out-File "$env:USERPROFILE\.fleet-agent\identity\SOUL.md" -Encoding UTF8

# Write your own NORTH_STAR.md
"Your custom goals" | Out-File "$env:USERPROFILE\.fleet-agent\identity\NORTH_STAR.md" -Encoding UTF8

# Write your own USER.md
"Details about you" | Out-File "$env:USERPROFILE\.fleet-agent\identity\USER.md" -Encoding UTF8
```
