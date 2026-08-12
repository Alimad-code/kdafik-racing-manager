\---

name: prompting-rules

description: Use this skill to govern how tasks should be approached in this repository so implementation stays incremental, scoped, and consistent.

\---

\# Prompting Rules Skill

\## Goal

Keep work in this repository incremental, structured, and aligned with the project’s priorities.

This skill is about execution discipline.

\## General approach

For significant tasks:

1\. understand the requested scope

2\. preserve current architecture and visual system

3\. make the smallest high-value change that solves the problem

4\. report clearly what changed

5\. identify what should happen next

\## Task handling rules

\### Prefer phased delivery

Do not try to build the whole application at once.

Prefer:

\- scaffold first

\- design system second

\- screens third

\- polish fourth

\- QA fifth

\- refactor after stability

\### Respect current project phase

Current priority is frontend v1: a polished single-player season flow backed by FastAPI through the repository boundary.

Do not drift into:

\- backend implementation in this frontend repository

\- advanced infrastructure

\- extra product modes

\- speculative enterprise abstractions

\### Preserve consistency

When changing screens or components:

\- follow existing tokens and patterns

\- do not invent alternate styles without reason

\- do not silently replace the visual language

\### Prefer concrete outputs

When asked to implement:

\- create files

\- modify code

\- improve components

\- wire routes

\- validate behavior

Do not answer only with abstract advice unless explicitly requested.

\## Scope control rules

Avoid:

\- adding features outside the ask

\- changing stack without reason

\- overengineering state management

\- introducing large new dependencies casually

\- turning simple components into framework-like systems

\## Refactoring rules

Refactor only when:

\- duplication is clearly harmful

\- structure is becoming unclear

\- reuse meaningfully improves maintainability

\- the change does not destabilize the app

Prefer targeted refactors over sweeping rewrites.

\## Communication/output rules

When completing work, clearly state:

1\. what was changed

2\. what assumptions were made

3\. what remains incomplete

4\. what the logical next step is

\## UI implementation rules

When building UI:

\- prefer motorsport credibility over novelty

\- prefer strong hierarchy over decorative flourish

\- prefer table/readability quality over card excess

\- prefer desktop clarity over premature responsive perfection

\- write new visible product UI copy in Russian by default; keep English only for intentional racing codes, driver abbreviations, API/debug text, or explicit user-approved exceptions

\## Data rules

When creating or editing data-facing code:

\- keep FastAPI as the current runtime direction

\- keep mock data believable when used as reference/test material

\- align data with domain types, API DTOs, and mappers

\- avoid random or sloppy placeholder values

\- do not reintroduce a mock-runtime fallback as a product goal

\## Testing/review rules

After significant UI work:

\- ensure routes still work

\- ensure core screens still render

\- ensure no critical console/runtime breakages

\- prefer practical verification over theoretical confidence

\## When uncertain

If a decision is ambiguous:

\- choose simpler over more complex

\- choose more consistent over more novel

\- choose more maintainable over more “clever”

\- choose the option that better preserves the current FastAPI repository boundary

\## Definition of done

A task is done when:

\- it solves the requested problem

\- it stays within scope

\- it preserves consistency

\- it leaves the project in a better state than before
