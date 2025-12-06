<!--
Sync Impact Report
Version change: N/A → 1.0.0
Modified principles: Principle 1 → Readability & Explicitness; Principle 2 → TDD-First & Isolated; Principle 3 → Automation Everywhere; Principle 4 → Simple, Disciplined Design; Principle 5 → Purposeful Comments & Rationale
Added sections: Development Workflow; Review & Quality Gates
Removed sections: None
Templates requiring updates (✅ updated / ⚠ pending): ✅ .specify/templates/plan-template.md; ✅ .specify/templates/spec-template.md; ✅ .specify/templates/tasks-template.md
Follow-up TODOs: None
-->

# Real Talk Coach Constitution

## Core Principles

### I. Readability & Explicitness
Code must favor clarity over clever tricks. Prefer straightforward flows, descriptive naming, and
explicit dependencies over hidden magic so maintainers can reason about behavior quickly.

### II. TDD-First & Isolated
All new work begins with tests. Write failing tests before implementation, rely on mocks/stubs for
external services, and iterate through red-green-refactor to keep scope tight and regressions
visible.

### III. Automation Everywhere
Automate repeatable work—linting, formatting, tests—and gate merges on passing pipelines. Local
commands should mirror CI so every developer can reproduce results without manual steps.

### IV. Simple, Disciplined Design
Apply KISS, DRY, SOLID, and YAGNI to keep designs minimal and cohesive. Add abstractions only when
needed, remove duplication with intention, and keep interfaces small and well-defined.

### V. Purposeful Comments & Rationale
Comments and docs must explain why decisions were made, tradeoffs considered, and constraints
accepted—not restate what the code already says. Keep rationale close to the code and update it as
behavior changes.

## Development Workflow
- Start from user stories and acceptance tests that are specific enough to automate; these tests
  define scope.
- Stub or mock external systems to keep the feedback loop fast and deterministic.
- Follow red-green-refactor: write a failing test, implement the smallest change to pass, then clean
  up while preserving readability.
- Prefer simple, explicit implementations first; defer abstractions until repeated needs are proven.
- Keep automation scripts and CI definitions as single sources of truth for linting, testing, and
  build commands.

## Review & Quality Gates
- Reviews verify readability, explicit control flow, and that rationale is captured in code comments
  or docs.
- Every change must include tests created first and passing automation (lint, format, test) before
  merge.
- Designs that add complexity must justify alignment with KISS/DRY/SOLID/YAGNI; unnecessary patterns
  are rejected.
- Mocks/stubs must be used in tests when touching external services to avoid flakiness and ensure
  determinism.
- Periodic audits sample merged work to ensure constitution compliance and to tune automation where
  friction appears.

## Governance
This constitution supersedes informal practices; variances require explicit approval and documented
justification in the relevant plan/spec. Amendments follow semantic versioning: MAJOR for breaking
governance or principle removals, MINOR for new principles or significant expansions, PATCH for
clarifications. Each amendment must record rationale and affected templates. Ratification occurs via
team approval and is recorded in version history; the latest version is authoritative in this
repository. Compliance reviews run at least once per release cycle to validate adherence and update
templates or automation when gaps are found.

**Version**: 1.0.0 | **Ratified**: 2025-12-06 | **Last Amended**: 2025-12-06
