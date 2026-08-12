---
name: project-memory
description: Use this skill when working on Kdafik Racing Manager and Codex needs to read, maintain, or update the living project memory in docs/project-memory.md; trigger before project work and after meaningful changes to architecture, routes, screens, data source, mock/backend integration, design system, tests, documentation, known risks, or roadmap.
---

# Project Memory Skill

## Goal

Keep `docs/project-memory.md` as the short, current onboarding memory for Kdafik Racing Manager so a new chat can understand the project without re-auditing the whole repository.

This skill is for this repository only.

## Required start-of-task routine

Before doing project work:

1. Read `AGENTS.md`.
2. Read `docs/project-memory.md`.
3. Treat `docs/project-memory.md` as the current source of truth for project state.

## When to update project memory

Update `docs/project-memory.md` in the same chat when meaningful changes affect any of these:

- routes or v1 screens;
- app architecture, folder boundaries, shared UI, or design system;
- `SeasonRepository`, Zustand store, API DTOs, mock data, backend integration, or active data source;
- build, lint, format, Playwright, or runtime quality status;
- known risks, important decisions, or next priorities;
- documentation that changes how future chats should understand the project.

Do not update project memory for tiny copy edits, one-off experiments, generated build output, screenshots, or changes that do not alter project understanding.

## Memory file rules

Keep `docs/project-memory.md` concise and practical:

- target 80 to 160 lines;
- write stable facts, current decisions, active risks, and next priorities;
- avoid dumping full audits, command logs, file inventories, or implementation narration;
- remove or rewrite stale notes instead of endlessly appending;
- move obsolete details into a brief `Resolved / Archived Notes` item only when useful.

## Required structure

Preserve these sections:

```md
# Kdafik Racing Manager Project Memory

Last updated: YYYY-MM-DD

## What This Project Is

## Current Implementation State

## Architecture Notes

## UX And Visual Direction

## Known Risks

## Recent Decisions

## Next Priorities
```

## Update style

- Prefer short bullets.
- Mention file paths only when they prevent ambiguity.
- Keep the memory useful for the next agent, not exhaustive for the current task.
- If technical checks were run, record only the result and any important failure.
- If checks were not run after a meaningful change, record nothing unless that absence is important for future work.
