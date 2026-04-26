---
name: codebase-memory
description: >
  Structured memory for this codebase. Load whenever working on any code task —
  writing features, debugging failures, explaining code to developers or users,
  tracing where an output comes from, adding CLI commands, tuning agent behavior,
  understanding the memory/Graphiti pipeline, or working with Neo4j/OpenAI config.
---

# Agent instructions
_Last updated: 2026-04-25_

This codebase has structured memory in the `AGENTS/` directory. Before starting
any task, understand what each document type is for and reason from there — do
not re-read the entire codebase from scratch.

## The memory structure

Five document types. Each answers a different category of question.

**`AGENTS/00_map.md`** — answers *where things are*
The structural index: modules, file paths, entry points, data model summary, test
and deploy commands. Start here on any new task to orient yourself.

**`AGENTS/01_hazards.md`** — answers *what not to do*
NEVERs, CAUTIONs, and CONVENTIONs. Read this before any write operation, before
touching the async/event loop code, and before modifying Graphiti initialization.

**`AGENTS/contracts/`** — answers *how to call something correctly*
One file per module. Each function/endpoint with non-obvious behavior has a contract
note: required invariants, side effects, return edge cases, traceability fields
(`Produces:`, `Consumed by:`), and failure modes.

**`AGENTS/02_business_logic.md`** — answers *what something means or calculates*
Key behavioral logic: how memory context is retrieved, how episodes are stored,
how search results are formatted, and how user isolation works.

**`AGENTS/03_narratives.md`** — answers *what something does and why it exists*
Plain-English module descriptions written for explanation. Use when asked to
explain the codebase to a developer or user, or to orient a new contributor.

**`AGENTS/playbooks/`** — answers *how to do a specific task in this repo*
Step-by-step instructions for common tasks specific to this codebase's conventions.
Always check here before improvising an approach.

## How to reason

Map any question to the document type that answers it, read that document, then act.

- *Where is X / what module handles X?* → `00_map.md`
- *Is it safe to do X / what should I never do?* → `01_hazards.md`
- *How do I call X correctly / what does X return?* → `contracts/`
- *How does memory retrieval / episode storage work?* → `02_business_logic.md`
- *What does module X do / why does it exist?* → `03_narratives.md`
- *How do I add a CLI command / tool / config var?* → `playbooks/`
- *Why did X fail / what does this error mean?* → `contracts/` (search `Failure modes:`), then `01_hazards.md`, then `03_narratives.md`
- *What produced output X / what calls function X?* → `contracts/` (search `Produces:` / `Consumed by:`)

## After completing a task

Update the memory if your task introduced any of the following:
- A new CLI command → update `playbooks/add_cli_command.md` and `contracts/main.md`
- A new tool → update `playbooks/add_tool.md` and `contracts/tools.md`
- A new config variable → update `contracts/config.md`
- A new `# HACK:` or `# WARNING:` comment → add to `01_hazards.md`
- A new module → add narrative to `03_narratives.md`, add row to `AGENTS.md` module index
- A renamed/moved module → update `00_map.md` and all cross-references
