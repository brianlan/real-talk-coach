# Feature Specification: Admin Data Management

**Feature Branch**: `002-admin-data-management`  
**Created**: 2025-12-11  
**Status**: Draft  
**Input**: User description: "I need to add management pages for admin to setup the data in the backend database, for example, create a new scenario, create skills or assign skills to a scenario something like that. In case I may miss something, you can supplment anything that you think is needed for a backend admin page to manage all the data."

## User Scenarios & Testing *(mandatory)*

Acceptance scenarios must be automatable and will drive TDD. Note any mocks/stubs required for
external systems to keep tests deterministic.

### User Story 1 - Manage skill library (Priority: P1)

Admins create, edit, and organize skills so scenarios can reference a consistent rubric.

**Why this priority**: Skills are foundational and required before scenario setup can be completed.

**Independent Test**: Create a new skill, edit it, and verify it appears in the skill list with updated metadata.

**Acceptance Scenarios**:

1. **Given** the admin opens the skills page, **When** they create a new skill with name, category, and rubric, **Then** the skill appears in the list and can be selected by scenarios.
2. **Given** a skill is used by at least one published scenario, **When** the admin attempts to delete it, **Then** the system blocks the deletion and lists affected scenarios.

---

### User Story 2 - Manage scenarios and assign skills (Priority: P1)

Admins create and publish scenarios by providing required details and assigning skills that will be scored later.

**Why this priority**: Scenarios drive the core practice experience and must be set up before trainees can use the product.

**Independent Test**: Create a scenario, assign skills, publish it, and verify it appears in the catalog.

**Acceptance Scenarios**:

1. **Given** required scenario fields are completed, **When** the admin publishes the scenario, **Then** it becomes available to trainees and shows the assigned skills.
2. **Given** a scenario is missing required details or skills, **When** the admin attempts to publish it, **Then** the system prevents publishing and shows specific validation errors.

---

### User Story 3 - Review and maintain session data (Priority: P2)

Admins review practice sessions and evaluations to keep data clean and resolve issues.

**Why this priority**: Operational oversight and cleanup helps maintain data quality and reduce support burden.

**Independent Test**: Locate a session, view its details and evaluation status, and delete it with confirmation.

**Acceptance Scenarios**:

1. **Given** sessions exist, **When** the admin filters by scenario or date range, **Then** the list updates to matching sessions with key metadata.
2. **Given** a session is selected, **When** the admin deletes it and confirms, **Then** the session and its related records are removed and no longer appear in listings.

---

### Edge Cases

- Attempting to publish a scenario without end criteria or personas.
- Assigning duplicate skills to the same scenario.
- Deleting a scenario that has associated sessions.
- Editing a skill that is referenced by published scenarios.
- Concurrent edits by two admins on the same record.

## Requirements *(mandatory)*

**Design Discipline**: Keep solutions simple (KISS, YAGNI, DRY, SOLID). Document rationale for any
complexity that remains.  
**Testing**: Requirements must be concrete enough to translate directly into automated tests written
before implementation, with mocks/stubs specified for any external services.

### Functional Requirements

- **FR-001**: System MUST restrict access to the admin management pages to authorized admins only.
- **FR-002**: Admins MUST be able to create, view, edit, and delete skills with name, category, and rubric details.
- **FR-003**: System MUST prevent deletion of any skill that is referenced by a published scenario and list the impacted scenarios.
- **FR-004**: Admins MUST be able to create, view, edit, and delete scenarios including category, title, description, objective, personas, end criteria, prompt, and limits.
- **FR-005**: Admins MUST be able to assign one or more skills to a scenario and define their display order.
- **FR-006**: System MUST prevent publishing scenarios that are missing required fields or have no assigned skills, and MUST display validation errors per field.
- **FR-007**: Admins MUST be able to set a scenario’s status to draft or published.
- **FR-008**: Admins MUST be able to search and filter skills and scenarios by name, category, and status.
- **FR-009**: Admins MUST be able to list sessions with filters for date range, scenario, and completion status.
- **FR-010**: Admins MUST be able to view a session’s transcript, evaluation status, and key metadata.
- **FR-011**: Admins MUST be able to delete a session only after explicit confirmation, and deletions MUST remove associated evaluations and media references.
- **FR-012**: System MUST display created/updated timestamps for skills and scenarios.
- **FR-013**: System MUST provide clear, user-friendly error messages for validation failures and blocked actions.

### Assumptions

- Admin access is provisioned out-of-band and only trusted internal users will use these pages.
- Content management is limited to skills, scenarios, and session records; trainee-facing flows are unchanged.
- Bulk import/export is out of scope for this release.

### Key Entities *(include if feature involves data)*

- **Admin User**: Authorized operator who can manage skills, scenarios, and session records.
- **Skill**: A rubric-based competency with name, category, and description used for evaluations.
- **Scenario**: A practice setup with objectives, personas, end criteria, and assigned skills.
- **Practice Session**: A completed or active practice record tied to a scenario and its evaluation.
- **Evaluation**: A scored outcome linked to a practice session and scenario skills.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Admins can publish a new scenario with assigned skills in under 5 minutes on first attempt.
- **SC-002**: At least 95% of admin publish attempts succeed without support intervention.
- **SC-003**: Admins can locate and open a specific scenario or skill using search or filters within 30 seconds.
- **SC-004**: Data quality improves such that 0 published scenarios are missing required fields or skills.
