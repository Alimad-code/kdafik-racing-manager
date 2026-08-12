---
name: frontend-architecture
description: Use this skill when creating or modifying the React frontend architecture, routing, folder structure, feature boundaries, shared UI, FastAPI repository integration, and test-fixture organization for the Formula manager project.
---

# Frontend Architecture Skill

## Goal

Build and maintain a clean, scalable frontend architecture for a Formula-style season manager web application.

This project is currently:

- frontend v1 for a single-player season flow;
- FastAPI-backed through `SeasonRepository`;
- desktop-first;
- portfolio-oriented;
- not pursuing mock runtime fallback as a v1 product goal.

## Stack assumptions

Preferred stack:

- React
- TypeScript
- Vite
- React Router
- Tailwind CSS
- shadcn/ui
- Zustand
- Zod
- lucide-react
- Playwright
- ESLint
- Prettier

Do not change the stack without explicit instruction.

## Architecture priorities

1. Clarity
2. Maintainability
3. Reuse
4. FastAPI integration isolated behind repository/API boundaries
5. Low complexity

## Folder structure guidance

Use the existing pragmatic modular structure:

```text
src/
  app/
    providers/
    router/
    layout/
  pages/
    login/
    home/
    season-setup/
    season-overview/
    practice-setup/
    practice-results/
    qualifying/
    qualifying-results/
    race-results/
    championship-summary/
  features/
    season/
      api/
      lib/
      model/
  entities/
  shared/
    ui/
    lib/
    config/
    hooks/
    constants/
tests/
  seasonApiFixture.ts
```

## Data boundary rules

- Keep pages dependent on store/repository APIs, not direct `fetch` calls.
- Keep FastAPI DTOs, mappers, and endpoint details inside `src/features/season/api`.
- Keep `seasonDataSource.ts` as the runtime source selector.
- Treat `backendSeasonRepository` as the active runtime source.
- Keep local test data in Playwright fixtures, not as a runtime repository.
- Do not spread backend-specific response shapes into page components.

## Routing rules

- Keep route names readable and stable.
- Do not add broken placeholder routes.
- The current v1 route set is `/login`, `/`, `/season-setup`, `/season-overview`, `/practice-setup`, `/practice-results`, `/qualifying`, `/qualifying-results`, `/race-results`, `/championship-summary`, and development-only `/style-guide`.

## Refactoring rules

- Prefer small, local refactors that reinforce current boundaries.
- Add abstractions only when they reduce real duplication or match an existing local pattern.
- Avoid broad rewrites when a targeted repository/store/page change solves the problem.

## Definition of done

Architecture work is done when:

- route-level responsibilities remain clear;
- API integration stays behind the repository boundary;
- shared UI remains reusable;
- mock data is not reintroduced as the active runtime path;
- the project remains easy to reason about for the next implementation prompt.
