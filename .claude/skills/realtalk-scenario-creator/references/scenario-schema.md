# Scenario Schema Reference

Complete field-by-field reference for Real Talk Coach scenarios. Use this when writing scenario JSON to confirm exact field names, types, and which system pipeline reads each field.

## Top-Level Structure

```json
{
  "metadata": { ... },
  "context": { ... },
  "simulationConfig": { ... },
  "evaluationConfig": { ... }
}
```

All four sections are required. The admin API rejects payloads missing any of them.

---

## Field Reference

### `metadata` — Admin catalog info

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Display name (shown in scenario list) |
| `slug` | string | no | URL-friendly identifier |
| `domain` | string | yes | Category domain: "Workplace", "Family", "Healthcare", "Education", etc. |
| `scenarioType` | string | yes | Communication type: "Negotiation", "Empathetic Listening", "Conflict Resolution", "Difficult Feedback", etc. |
| `difficulty` | string | yes | "Easy", "Medium", or "Hard" |
| `conflictLevel` | string | yes | "Low", "Medium", or "High" |
| `estimatedDurationMinutes` | number | yes | Expected practice duration |
| `tags` | string[] | yes | Searchable tags |

**Pipeline visibility:** Not sent to roleplay AI. `title` is sent to evaluator. Rest is admin/internal only.

---

### `context` — Situation background

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `situation` | string | yes | What triggered the conversation |
| `background` | string | yes | Additional context and history |
| `setting` | string | yes | Where and when the conversation takes place |

**Pipeline visibility:** Sent to BOTH roleplay AI (in "SCENARIO CONTEXT" section) and evaluator (as `scenario_context`).

---

### `simulationConfig` — Roleplay configuration

#### `simulationConfig.ai` — The character the AI plays

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Character name (used as bot display name) |
| `role` | string | yes | Character's role/title |
| `personality` | string[] | yes | Surface personality traits (3-5 items) |
| `motivations` | string[] | yes | What drives the character underneath (3-4 items) |
| `constraints` | string[] | yes | External/internal limits on behavior (3-4 items) |
| `tendencies` | string[] | yes | Specific behavioral patterns — most important field (5-7 items) |
| `knowledge` | string[] | yes | What the character knows going in |
| `emotionalState` | string | yes | Current mood/ emotional state |

**Pipeline visibility:** All fields sent to roleplay AI in "ROLE YOU ARE PLAYING" section. NOT sent to evaluator.

#### `simulationConfig.trainee` — The trainee's persona

Same sub-fields as `ai`. However, the prompt builder only reads `name`, `role`, `knowledge`, and `emotionalState` from the trainee. The remaining fields (`personality`, `motivations`, `constraints`, `tendencies`) exist for completeness and are NOT sent to the roleplay AI or evaluator.

**Pipeline visibility:** Only `name`, `role`, `knowledge`, `emotionalState` sent to AI (in "TRAINEE ROLE" section).

#### `simulationConfig.language`

String: "English" or "Chinese". Determines the language instruction in the prompt.

#### `simulationConfig.conversationStart`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `speakerRoleId` | string | yes | Who speaks first. Normalized: "trainee"/"employee"/"user"/"learner"/"candidate" → trainee starts. "ai"/"assistant"/"bot"/"coach"/"manager" → AI starts. |
| `initialPromptToUser` | string | yes* | Shown to trainee if trainee speaks first. Instruction for how to begin. |

*Required when `speakerRoleId` maps to "trainee".

#### `simulationConfig.conversationRules`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `stayInCharacter` | boolean | yes | AI must stay in role |
| `allowNarration` | boolean | yes | Allow stage directions |
| `coachingAllowed` | boolean | yes | Allow coaching interjections |
| `tone` | string | yes | Conversation tone description |

**Pipeline visibility:** NOT sent to roleplay AI explicitly — the prompt builder enforces these via hardcoded rules instead.

#### `simulationConfig.conversationDynamics`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `typicalBehaviors` | string[] | yes | What the AI typically does (4-5 behavioral patterns) |
| `possibleResponses` | string[] | yes | Actual dialogue snippets the AI might use (6-8 items) |

**Pipeline visibility:** Sent to roleplay AI in "REALISTIC BEHAVIOR" section.

#### `simulationConfig.decisionConstraints`

Free-form JSON object. Rendered as nested bullet points. Use for scenario-specific rules like:
- Thresholds for the AI's openness/resistance
- Safe topics for building rapport
- Behaviors that trigger shutdown
- The staged path from resistance to openness

**Pipeline visibility:** Sent to roleplay AI in "REALISTIC BEHAVIOR" section under "Keep the following constraints in mind".

#### `simulationConfig.conversationEndConditions`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `possibleEndStates` | string[] | yes | Possible conversation outcomes (2-4 items) |

**Pipeline visibility:** Sent to roleplay AI in "CONVERSATION FLOW" section.

---

### `evaluationConfig` — Scoring configuration

**Pipeline visibility:** NOT sent to roleplay AI. All fields sent to evaluator LLM.

#### `evaluationConfig.learningObjectives`

`string[]` — What the trainee should learn/demonstrate (4-5 items). Shown to evaluator as a bullet list.

#### `evaluationConfig.evaluationCriteria`

Array of objects. Each criterion has:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique snake_case identifier. Used as `skillId` in scores. |
| `description` | string | yes | What to look for. Write for LLM scoring — specific behaviors, not vague qualities. |

The evaluator uses each `id` as the `skillId` in its score output. These IDs must match keys in `scoring.criteriaWeighting`.

#### `evaluationConfig.skillsAssessed`

`string[]` — Skill labels for the evaluator (5-6 items). These are descriptive, not scored individually.

#### `evaluationConfig.scoring`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scale` | string | yes | Always "1-5" |
| `criteriaWeighting` | object | yes | Maps criterion IDs to weights (should sum to ~1.0) |

#### `evaluationConfig.evaluationInstructionsForLLM`

`string` — Custom instructions for the evaluator. Use to set expectations, focus attention, and prevent harsh scoring. This is your control valve for evaluation quality.

---

## Validation Checklist

Run these checks before storing:

- [ ] All 4 top-level sections present: `metadata`, `context`, `simulationConfig`, `evaluationConfig`
- [ ] `metadata` has: `title`, `domain`, `scenarioType`, `difficulty`, `conflictLevel`, `estimatedDurationMinutes`, `tags`
- [ ] `context` has: `situation`, `background`, `setting`
- [ ] `simulationConfig.ai` has: `name`, `role`, `personality`, `motivations`, `constraints`, `tendencies`, `knowledge`, `emotionalState`
- [ ] `simulationConfig.trainee` has same sub-fields as `ai`
- [ ] `simulationConfig.conversationStart` has `speakerRoleId` and `initialPromptToUser`
- [ ] `simulationConfig.conversationDynamics` has `typicalBehaviors` and `possibleResponses`
- [ ] `simulationConfig.conversationEndConditions` has `possibleEndStates`
- [ ] `evaluationConfig.evaluationCriteria` is non-empty array
- [ ] `evaluationConfig.skillsAssessed` is non-empty array
- [ ] All `evaluationCriteria[].id` values exist in `scoring.criteriaWeighting`
- [ ] `scoring.criteriaWeighting` values sum to approximately 1.0
- [ ] `speakerRoleId` is a recognizable role identifier

## Prompt Builder Field Map

For reference, here's exactly what the roleplay AI sees in its system prompt:

| Prompt Section | Scenario Fields Injected |
|---------------|------------------------|
| ROLE YOU ARE PLAYING | `ai.name`, `ai.role`, `ai.personality`, `ai.motivations`, `ai.constraints`, `ai.tendencies`, `ai.emotionalState` |
| SCENARIO CONTEXT | `context.situation`, `context.background`, `context.setting` |
| TRAINEE ROLE (FOR CONTEXT ONLY) | `trainee.name`, `trainee.role`, `trainee.knowledge`, `trainee.emotionalState` |
| ROLEPLAY RULES | Hardcoded (stay in character, no narration, no coaching, no evaluation hints) |
| CONVERSATION STYLE | Hardcoded (natural tone, ask questions, let trainee drive) |
| REALISTIC BEHAVIOR | `conversationDynamics.typicalBehaviors`, `possibleResponses`, `decisionConstraints` |
| CONVERSATION FLOW | `conversationEndConditions.possibleEndStates` |
| LANGUAGE | Resolved from `language` parameter or `simulationConfig.language` |
| START OF SIMULATION | `conversationStart.speakerRoleId` |

The prompt also includes these hardcoded behavioral guardrails:
- "Do NOT help the trainee succeed."
- "Do NOT immediately agree with the trainee's request unless sufficient justification is provided."
- "Do NOT mention evaluation criteria or training mechanics."
