# Research: Admin Data Management

## Decision 1: Admin access control

**Decision**: Use a pre-shared admin token for all admin endpoints and pages.

**Rationale**: Keeps setup minimal for internal tools while still enforcing explicit authorization.

**Alternatives considered**:
- Full identity provider integration (rejected: higher setup cost and scope).
- IP allowlist only (rejected: insufficient for distributed access and URL leakage risk).

## Decision 2: Concurrent edit handling

**Decision**: Use optimistic concurrency checks and reject stale updates.

**Rationale**: Prevents silent overwrites without adding heavy locking or complex coordination.

**Alternatives considered**:
- Last write wins (rejected: silent data loss).
- Record locking (rejected: higher operational complexity for internal admin use).

## Decision 3: Deletion and data safety

**Decision**: Use soft-delete with restore for skills and scenarios; block scenario deletion when
sessions exist; block skill deletion when referenced by published scenarios.

**Rationale**: Protects production data and preserves auditability while allowing recovery.

**Alternatives considered**:
- Hard delete only (rejected: high risk of irreversible data loss).
- Automatic cascade deletes (rejected: risks orphaning history and evaluations).

## Decision 4: Audit logging

**Decision**: Record audit log entries for admin create/update/delete actions.

**Rationale**: Supports traceability and operational accountability without excessive logging.

**Alternatives considered**:
- No audit log (rejected: insufficient operational visibility).
- Log all admin reads (rejected: over-collection without clear value).
