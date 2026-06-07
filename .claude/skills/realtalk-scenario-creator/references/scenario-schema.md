# Scenario Schema Reference

Use this reference for exact field names and current pipeline visibility.

## Top-Level Shape

```json
{
  "metadata": {},
  "context": {},
  "simulationConfig": {},
  "evaluationConfig": {}
}
```

The admin API requires all four top-level sections. The frontend/admin type expects the richer structure below.

## `metadata`

Admin catalog data.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `title` | string | yes | Display name. Sent to evaluator as scenario title. |
| `slug` | string | no | URL-friendly identifier. |
| `domain` | string | yes | Category/domain. |
| `scenarioType` | string | yes | Communication type. |
| `difficulty` | string | yes | Display label. Existing data may use English or Chinese labels. |
| `conflictLevel` | string | yes | Display label. Existing data may use English or Chinese labels. |
| `estimatedDurationMinutes` | number | yes | Expected practice duration. |
| `tags` | string[] | yes | Search/filter labels. |

Roleplay visibility: not sent to roleplay AI.

Evaluation visibility: `title` only.

## `context`

Shared situation background.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `situation` | string | yes | Immediate conflict and what triggered the talk. |
| `background` | string | yes | History, hidden pressure, character incentives. |
| `setting` | string | yes | Where/when the conversation starts. |

Roleplay visibility: all fields are injected.

Evaluation visibility: all fields are sent as scenario context.

## `simulationConfig`

### `simulationConfig.ai`

The character played by the AI.

| Field | Type | Required | Roleplay Visibility |
| --- | --- | --- | --- |
| `name` | string | yes | Injected; used as bot display name. |
| `role` | string | yes | Injected. |
| `personality` | string[] | yes | Injected. |
| `motivations` | string[] | yes | Injected. |
| `constraints` | string[] | yes | Injected; strong behavior lever. |
| `tendencies` | string[] | yes | Injected; strong behavior lever. |
| `knowledge` | string[] | yes | Stored, but **not injected by current prompt builder**. Do not rely on this for live behavior. |
| `emotionalState` | string | yes | Injected. |

For behavior-critical facts, duplicate or move them into `context`, `constraints`, `tendencies`, `conversationDynamics`, or `decisionConstraints`.

### `simulationConfig.trainee`

The user's role.

Same sub-fields as `ai`.

Roleplay visibility:

- Injected: `name`, `role`, `knowledge`, `emotionalState`
- Not injected: `personality`, `motivations`, `constraints`, `tendencies`

Use non-injected trainee fields for admin readability and scenario design, not for live roleplay behavior.

### `simulationConfig.language`

Use `zh` for Chinese practice and `en` for English practice. The prompt builder also understands labels such as `Chinese`, but current UI/session APIs use `zh`/`en`.

### `simulationConfig.conversationStart`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `speakerRoleId` | string | yes | Prefer exact values `trainee` or `ai`. The backend normalizes some aliases, but the frontend type is stricter. |
| `initialPromptToUser` | string | yes when trainee starts | Shown/sent when trainee starts. |

If `speakerRoleId` resolves to `trainee`, the opening prompt is sent without LLM generation. If it resolves to `ai`, `opening_prompt_service.py` may generate the first AI line.

### `simulationConfig.conversationRules`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `stayInCharacter` | boolean | yes | Stored/admin field. |
| `allowNarration` | boolean | yes | Stored/admin field. |
| `coachingAllowed` | boolean | yes | Stored/admin field. |
| `tone` | string | yes | Stored/admin field. |

Current roleplay prompt uses hardcoded equivalent rules instead of rendering this object directly.

### `simulationConfig.conversationDynamics`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `typicalBehaviors` | string[] | yes | Injected under realistic behavior. Describe response rhythm and triggers. |
| `possibleResponses` | string[] | yes | Injected examples. Keep these aligned with desired resistance/cooperation level. |

Avoid over-cooperative snippets unless the persona should soften quickly.

### `simulationConfig.decisionConstraints`

Free-form JSON object. Injected as nested bullets under "Keep the following constraints in mind".

Use this for:

- awareness/resistance thresholds
- early-turn rules
- concession ceilings
- shutdown triggers
- safe topics
- deflection patterns
- path to partial agreement
- "do not make the AI..." guardrails

This is the best place for scenario-specific state-machine behavior.

### `simulationConfig.conversationEndConditions`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `possibleEndStates` | string[] | yes | Injected. Include partial success and failure paths. |

## `evaluationConfig`

Not sent to the roleplay AI. Sent to the evaluator after the session.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `learningObjectives` | string[] | yes | Sent to evaluator. |
| `evaluationCriteria` | `{id, description}[]` | yes | Criterion ids become score `skillId`s. |
| `skillsAssessed` | string[] | yes | Descriptive labels. |
| `scoring.scale` | string | yes | Use `"1-5"`. |
| `scoring.criteriaWeighting` | object | yes | Keys must match criterion ids. |
| `evaluationInstructionsForLLM` | string | yes | Sets grading expectations and partial-success logic. |

## Validation Checklist

- [ ] Four top-level sections exist.
- [ ] Required `metadata` and `context` fields exist.
- [ ] `simulationConfig.ai` and `.trainee` have the persona sub-fields.
- [ ] `language` is `zh` or `en`.
- [ ] `conversationStart.speakerRoleId` is `trainee` or `ai`.
- [ ] `conversationStart.initialPromptToUser` exists if trainee starts.
- [ ] `conversationDynamics.typicalBehaviors` and `possibleResponses` are non-empty.
- [ ] `decisionConstraints` includes thresholds for resistant personas.
- [ ] `conversationEndConditions.possibleEndStates` includes realistic partial/failure states.
- [ ] `evaluationCriteria` and `skillsAssessed` are non-empty.
- [ ] Every criterion id has a weighting key.
- [ ] Weight values sum to approximately 1.0.
- [ ] Live prompt generation includes the behavior-critical rules.

## Prompt Field Map

| Prompt Section | Fields Injected |
| --- | --- |
| ROLE YOU ARE PLAYING | `ai.name`, `ai.role`, `ai.personality`, `ai.motivations`, `ai.constraints`, `ai.tendencies`, `ai.emotionalState` |
| SCENARIO CONTEXT | `context.situation`, `context.background`, `context.setting` |
| TRAINEE ROLE | `trainee.name`, `trainee.role`, `trainee.knowledge`, `trainee.emotionalState` |
| ROLEPLAY RULES | Hardcoded no coaching/no narration/no evaluation mechanics |
| CONVERSATION STYLE | Hardcoded natural tone, ask questions, let trainee drive |
| REALISTIC BEHAVIOR | `conversationDynamics.typicalBehaviors`, `possibleResponses`, `decisionConstraints` |
| CONVERSATION FLOW | `conversationEndConditions.possibleEndStates` |
| LANGUAGE | Session language or `simulationConfig.language` |
| START OF SIMULATION | `conversationStart.speakerRoleId` |
