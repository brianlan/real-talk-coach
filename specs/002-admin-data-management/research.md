# Research: Admin Data Management

## Decision 1: Admin-only access model

**Decision**: Use a lightweight, pre-shared admin access mechanism suitable for internal tools, with
explicit authorization checks on every admin endpoint.

**Rationale**: The feature is for trusted internal users and requires minimal operational overhead
while still preventing accidental exposure to trainees.

**Alternatives considered**:
- Full identity provider integration (rejected: adds scope and setup complexity for an internal-only MVP).
- IP allowlist only (rejected: brittle for distributed teams and does not protect against leaked URLs).

## Decision 2: Skill/scenario reference safety

**Decision**: Block deletion of skills that are referenced by published scenarios and block
scenario deletion when it has associated sessions unless an explicit override action is taken.

**Rationale**: Prevents breaking live content and protects session history integrity while still
allowing controlled maintenance.

**Alternatives considered**:
- Silent cascading deletes (rejected: high risk of unintended data loss).
- Automatic unpublish on delete (rejected: ambiguous behavior and potential surprise).

## Decision 3: Admin UX focus

**Decision**: Provide focused admin workflows for skills, scenarios, and sessions with clear
validation and confirmation for destructive actions.

**Rationale**: Keeps the admin experience narrow and reliable while meeting the core data
management needs from the spec.

**Alternatives considered**:
- Broad admin dashboard with analytics and reporting (rejected: out of scope for initial admin CRUD).
- Bulk import/export tools (rejected: explicitly out of scope in assumptions).
