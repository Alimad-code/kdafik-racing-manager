\---

name: frontend-quality-gates

description: Use this skill when validating, polishing, or reviewing frontend implementation quality for the Formula manager project.

\---

\# Frontend Quality Gates Skill

\## Goal

Ensure the frontend is clean, stable, coherent, and portfolio-worthy.

This skill applies after implementing screens, components, refactors, or visual changes.

\## Quality priorities

1\. No broken user flow

2\. No broken routes

3\. No major visual inconsistency

4\. No obvious console/runtime errors

5\. No type chaos

6\. No lint chaos

7\. Reuse over duplication

8\. UI credibility over raw feature count

\## Required checks

Whenever substantial frontend work is done, verify:

\- project builds

\- project typechecks

\- lint passes or has only intentional known exceptions

\- no critical route is broken

\- no primary screen is visually incomplete

\- no obvious console errors appear during main flow

\- no dead imports/components accumulate unnecessarily

\## Minimum commands expectation

Use the project’s actual scripts, but typically verify:

\- install succeeds

\- dev starts

\- build succeeds

\- lint succeeds

\- typecheck succeeds

\- Playwright smoke checks pass if configured

\## Visual consistency checks

Inspect whether:

\- page headers follow one pattern

\- table styles are unified

\- status colors are consistent

\- action buttons follow hierarchy

\- spacing rhythm is coherent

\- dark theme contrast remains readable

\- the app still feels motorsport-like

\## Reuse checks

Before approving implementation, check for repeated patterns that should be shared:

\- page title sections

\- table shells

\- status pills

\- stats rows

\- summary cards

\- metadata blocks

Refactor repeated UI where reasonable.

\## Type quality checks

\- avoid `any` unless truly justified

\- prefer clear domain interfaces/types

\- avoid giant untyped mock objects

\- keep data structures aligned with the current FastAPI repository boundary

\## Accessibility baseline

Do not aim for perfect enterprise accessibility at this stage, but ensure:

\- buttons are real buttons

\- inputs have labels

\- headings are structured

\- contrast is acceptable

\- keyboard navigation is not obviously broken

\- status information is not color-only when avoidable

\## Performance baseline

Avoid obvious frontend waste:

\- giant unnecessary renders

\- huge inline arrays inside render paths

\- excessive local repeated data transformations

\- large component files doing too much at once

\## UX quality baseline

Check:

\- primary action is visible

\- route flow is understandable

\- setup/results screens are not cluttered

\- important standings/timing values are easy to scan

\- “continue” path through the product is obvious

\## Anti-patterns to flag

\- placeholder text left in key screens

\- routes that open empty layouts

\- duplicate design patterns implemented differently

\- overreliance on temporary hardcoded hacks

\- styling done ad hoc instead of through the system

\- visual regressions after refactor

\## Output expectations when used

When this skill is applied, produce:

1\. summary of checks performed

2\. issues found

3\. issues fixed

4\. remaining non-critical issues

5\. recommended next cleanup step if needed

\## Definition of done

A frontend change passes quality gates when:

\- the app is stable

\- the flow is coherent

\- the UI still matches the intended visual direction

\- no critical technical debt was introduced
