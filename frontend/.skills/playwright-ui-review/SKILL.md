\---

name: playwright-ui-review

description: Use this skill when reviewing the running frontend through browser automation to catch broken routes, missing sections, layout issues, and visible UX defects.

\---

\# Playwright UI Review Skill

\## Goal

Use browser automation to validate that the Formula manager frontend works as expected across main routes and key user flows.

This is not a deep E2E product test suite.

This is a practical review process for catching obvious frontend issues quickly.

\## Primary objectives

\- verify main routes render

\- verify key UI sections are present

\- verify layout is not obviously broken

\- detect critical console errors

\- detect missing navigation/action paths

\- catch major visual regressions

\- improve confidence after implementation or refactor

\## Core review flow

Review these routes/pages where implemented:

\- Login

\- Home Dashboard

\- Team Selection / Season Setup

\- Season Overview

\- Practice Setup

\- Practice Results

\- Qualifying

\- Qualifying Results

\- Race Results

\- Championship Summary

\## What to check on each route

1\. Route loads successfully

2\. Page title/header is visible

3\. Primary action is visible

4\. Key data block/table is visible

5\. Navigation/back/continue path is available if expected

6\. No catastrophic layout break

7\. No blocking console errors

8\. No obviously missing mock data rendering

\## Desktop-first rule

Prioritize desktop viewport review first.

Only review smaller widths if explicitly asked or if responsive issues are severe.

\## Severity levels

\### Critical

\- route fails to load

\- major UI section missing

\- broken navigation path

\- blocking runtime error

\- completely broken layout

\### Important

\- table unreadable

\- header/action hierarchy broken

\- spacing causes strong confusion

\- state/action labels inconsistent

\- important content off-screen or badly aligned

\### Minor

\- polish issues

\- inconsistent spacing

\- slightly awkward alignment

\- secondary copy inconsistency

\## Behavior when issues are found

\- fix critical issues immediately if possible

\- fix important issues if low-risk

\- report minor issues even if not fixed

\- do not redesign the product during review

\- do not introduce major architectural changes unless necessary to solve a real defect

\## Review output format

After review, summarize:

1\. pages checked

2\. critical issues found

3\. important issues found

4\. fixes applied

5\. known remaining issues

6\. suggested next pass

\## Anti-patterns to avoid

\- turning QA review into a full redesign

\- rewriting components without cause

\- fixing tiny issues while leaving broken routes unfixed

\- changing design language during QA

\- adding test complexity that slows down iteration without value

\## Definition of done

The review is successful when:

\- core routes are functional

\- primary screens visibly work

\- critical regressions are resolved

\- a short trustworthy QA summary exists
