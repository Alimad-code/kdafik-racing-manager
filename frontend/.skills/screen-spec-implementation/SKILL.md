\---

name: screen-spec-implementation

description: Use this skill when implementing or refining the frontend v1 screens and FastAPI-backed user flow for the Formula manager frontend based on the agreed product structure.

\---

\# Screen Spec Implementation Skill

\## Goal

Implement the frontend v1 screens of the Formula manager in a consistent, believable, high-quality way using the agreed design language and current FastAPI-backed state.

This skill focuses on:

\- screen structure

\- information hierarchy

\- required blocks

\- route-level coherence

\- realistic FastAPI-backed flow

\## Frontend v1 screens

Required screens:

1\. Login

2\. Home Dashboard

3\. Team Selection / Season Setup

4\. Season Overview

5\. Practice Setup

6\. Practice Results

7\. Qualifying

8\. Qualifying Results

9\. Race Results

10\. Championship Summary

\## Routing expectation

Keep route names readable.

Example:

\- `/login`

\- `/`

\- `/season/setup`

\- `/season/overview`

\- `/season/practice`

\- `/season/practice/results`

\- `/season/qualifying`

\- `/season/qualifying/results`

\- `/season/race/results`

\- `/season/championship`

This can vary slightly, but the route map must stay simple.

\## Global app shell

Main product screens should share a coherent shell with:

\- top app header

\- current season or stage context

\- current budget or progress summary if useful

\- navigation or contextual back/next actions

Do not make the shell overly complex.

\## Screen requirements

\### 1. Login

Purpose:

\- simple entry point

\- visually aligned with the main product

Should include:

\- project title/branding

\- login form

\- optional supporting copy

\- clear CTA

Should not include:

\- marketing-site complexity

\- heavy auth features

\### 2. Home Dashboard

Purpose:

\- starting point after entering the app

Should include:

\- best result / season summary

\- main CTA to start or continue season

\- small recent stats or summary panel

\- lightweight overview of current progress if a season exists

Primary action:

\- start season or continue season

\### 3. Team Selection / Season Setup

Purpose:

\- choose two drivers and one team

\- understand budget impact

Must include:

\- driver slot 1

\- driver slot 2

\- team slot

\- budget panel

\- cost breakdown

\- confirm action

Selection UI should feel structured and premium.

Do not make it look like a shopping catalog.

\### 4. Season Overview

Purpose:

\- replace complex map with a clear stage calendar board

Must include:

\- list or board of stages

\- current stage highlight

\- completed/upcoming/current states

\- standings snapshot

\- CTA to proceed to current stage

Optional:

\- small track/weather preview for current stage

\### 5. Practice Setup

Purpose:

\- configure the cars before a practice run

Must include:

\- current stage and track context

\- driver/car summaries

\- setup controls

\- total setup cost

\- primary action to run practice

Priority:

\- action clarity over information overload

\### 6. Practice Results

Purpose:

\- show practice outcome and support next decision

Must include:

\- timing/results table

\- setup interpretation summary

\- stability/performance feedback

\- next action

Optional:

\- recommendation panel

\- warning state for damage or repair needs

\### 7. Qualifying

Purpose:

\- final pre-session summary before qualifying

Must include:

\- driver/car state

\- track summary

\- qualifying start CTA

Keep this screen tighter than practice setup.

\### 8. Qualifying Results

Purpose:

\- show the starting grid

Must include:

\- grid or grid-style results presentation

\- lap times or NO TIME status

\- status handling for incidents

\- CTA to proceed to race

Must feel official and clean.

\### 9. Race Results

Purpose:

\- show finishing order and core race outcome

Must include:

\- race results table

\- gap presentation

\- best lap summary

\- return/proceed action

Optional:

\- compact track/weather recap

\- small event summary

\### 10. Championship Summary

Purpose:

\- end-of-season standings summary

Must include:

\- driver standings

\- team standings

\- season finish action

\- summary of user result / best result

This should feel like a proper season-ending screen, not an afterthought.

\## Information hierarchy rules

For every screen:

\- identify one dominant block

\- identify one primary action

\- keep secondary information clearly subordinate

\- avoid multiple equally loud components competing for attention

\## State requirements

For important screens, support:

\- default loaded state

\- empty or not-started state where applicable

\- warning state if relevant

\- believable backend-driven data and controlled missing-data states

\## Consistency rules

Across all screens, keep consistent:

\- page titles

\- section titles

\- status labels

\- table structure

\- action area placement

\- metadata patterns

\## Anti-patterns to avoid

\- giant one-off page components with no reuse

\- inconsistent page header patterns

\- random per-screen styling

\- overcomplicated layouts for simple actions

\- adding features outside defined v1 scope

\- replacing season overview with a complex map before needed

\## Definition of done

Screen implementation is done when:

\- all v1 routes exist

\- screens feel part of the same product

\- main user flow is believable

\- tables and actions are coherent

\- no screen feels like a rough placeholder
