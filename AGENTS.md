# Agent Memory

This repo's agent memory lives in `AGENTS/`. It is generated and maintained
by the `codebase-documenter` skill and read by the `codebase-navigator` skill.

_Last updated: 2026-04-25_

## What's in here

| Document | Purpose |
|----------|---------|
| `AGENTS/00_agent_instructions.md` | Agent entry point — read this first |
| `AGENTS/00_map.md` | Module index, entry points, stack, test/deploy commands |
| `AGENTS/01_hazards.md` | NEVERs, CAUTIONs, and team conventions |
| `AGENTS/02_business_logic.md` | Memory retrieval, episode storage, search formatting logic |
| `AGENTS/03_narratives.md` | Plain-English module descriptions |
| `AGENTS/contracts/` | Per-module call contracts and traceability |
| `AGENTS/playbooks/` | Step-by-step task instructions for this repo |

## Module index

| Module | Path | Contract |
|--------|------|---------|
| agent | `src/agent.py` | `→ AGENTS/contracts/agent.md` |
| graphiti_client | `src/graphiti_client.py` | `→ AGENTS/contracts/graphiti_client.md` |
| tools | `src/tools.py` | `→ AGENTS/contracts/tools.md` |
| config | `src/config.py` | `→ AGENTS/contracts/config.md` |
| user_session | `src/user_session.py` | `→ AGENTS/contracts/user_session.md` |
| visualizer | `src/visualizer.py` | `→ AGENTS/contracts/visualizer.md` |
| main (CLI) | `main.py` | `→ AGENTS/contracts/main.md` |

## Updating this memory

Run `codebase-documenter` to regenerate after significant code changes.
For small changes, the documenter's incremental update mode (Phase 7) will
surgically update only the affected documents.
