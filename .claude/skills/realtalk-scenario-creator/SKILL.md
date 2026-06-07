---
name: realtalk-scenario-creator
description: >
  Create, validate, publish, and iterate production Real Talk Coach practice scenarios.
  Use when the user wants a new conversation practice scenario, roleplay simulation,
  difficult conversation exercise, scenario JSON, AI persona, trainee persona, evaluation
  rubric, or changes to an existing scenario's roleplay behavior/evaluation. Covers
  requirement gathering, scenario design, prompt-builder-aware behavior controls,
  evaluation criteria, admin API storage, publishing, and post-test tuning.
---

# Real Talk Scenario Creator

Create scenarios that work with the current Real Talk Coach architecture, not generic roleplay JSON. A good scenario has two separate designs:

- **Roleplay behavior**: `context` + `simulationConfig` shape what the realtime voice AI does.
- **Coaching/evaluation**: `evaluationConfig` shapes post-session scoring. It is not sent to the roleplay AI.

Always read `references/scenario-schema.md` before writing or editing JSON. Read `references/scenario-design-patterns.md` when designing difficult, resistant, avoidant, defensive, emotionally guarded, manipulative, or high-stakes personas.

## Current Architecture

The live roleplay prompt is built by `backend/app/services/e2e_prompt_builder.py` and sent as `dialog.system_role` in the E2E voice socket.

The roleplay AI sees:

- `simulationConfig.ai.name`, `role`, `personality`, `motivations`, `constraints`, `tendencies`, `emotionalState`
- `context.situation`, `background`, `setting`
- `simulationConfig.trainee.name`, `role`, `knowledge`, `emotionalState`
- `simulationConfig.conversationDynamics.typicalBehaviors`
- `simulationConfig.conversationDynamics.possibleResponses`
- `simulationConfig.decisionConstraints`
- `simulationConfig.conversationEndConditions.possibleEndStates`
- `simulationConfig.language` or session language
- `simulationConfig.conversationStart.speakerRoleId`

The roleplay AI does **not** see:

- `evaluationConfig`
- `simulationConfig.ai.knowledge` in the current prompt builder
- `simulationConfig.trainee.personality`, `motivations`, `constraints`, `tendencies`
- `conversationRules` as data; equivalent hardcoded rules are used instead

Put behavior-critical facts in injected fields, especially `context`, `ai.constraints`, `ai.tendencies`, `conversationDynamics`, and `decisionConstraints`. Do not rely on `ai.knowledge` for live behavior.

## Workflow

### 1. Gather Requirements

Get enough detail to build a realistic tension:

- Topic: what conversation the trainee must practice.
- AI role: who the AI plays, their surface behavior, hidden motives, blind spots, fears, and incentives.
- Trainee role: who the user plays and what they need to achieve.
- Core tension: why the AI will not naturally give the trainee what they want.
- Success: what good communication looks like even if the AI only partially changes.
- Language: use `zh` for Chinese practice and `en` for English practice. Scenario content should match the chosen practice language.

If the user gives a thin prompt, ask for hidden motivations, shutdown triggers, safe rapport topics, and realistic partial success.

### 2. Design Roleplay Behavior

Use the injected fields intentionally:

- `context`: factual situation and backstory both AI and evaluator should know.
- `ai.personality`: visible traits.
- `ai.motivations`: what the character is protecting or pursuing.
- `ai.constraints`: hard limits, blind spots, and conditions before they soften.
- `ai.tendencies`: turn-by-turn patterns with triggers. This is one of the strongest behavior levers.
- `conversationDynamics.typicalBehaviors`: expected response rhythm.
- `possibleResponses`: exact lines the AI can imitate. Include deflections and partial concessions, not only cooperative lines.
- `decisionConstraints`: scenario-specific state machine, thresholds, ceilings, shutdown triggers, and agreement pacing.
- `conversationEndConditions`: realistic outcomes, including partial progress and failed conversations.

For resistant personas, explicitly define:

- What the AI does in the first 3-5 turns.
- What is not enough to make them concede.
- What evidence or repeated user behavior changes their stance.
- What size of concession is allowed early.
- What they must never do too soon.

### 3. Design Evaluation

Build `evaluationConfig` around user behavior, not whether the AI fully cooperates.

Use 5-6 criteria. Each criterion needs:

- `id`: stable snake_case identifier.
- `description`: observable behavior the evaluator can score from transcript.

Good criteria measure:

- Opening quality.
- Specific facts and impact.
- Separation of person from problem.
- Boundary/request clarity.
- Handling deflection, minimization, shutdown, or emotional pressure.
- Concrete next step and follow-through.

In `evaluationInstructionsForLLM`, state realistic expectations. If the AI persona is meant to resist, say that the trainee should not be penalized merely because the AI only partially accepts.

Every `evaluationCriteria[].id` must appear in `scoring.criteriaWeighting`; weights should sum to 1.0.

### 4. Validate Before Storing

Check:

- Top level has `metadata`, `context`, `simulationConfig`, `evaluationConfig`.
- `metadata` has title, domain, scenarioType, difficulty, conflictLevel, estimatedDurationMinutes, tags.
- `context` has situation, background, setting.
- `simulationConfig.ai` and `.trainee` have name, role, personality, motivations, constraints, tendencies, knowledge, emotionalState.
- `language` is `zh` or `en`.
- `conversationStart.speakerRoleId` is `trainee` or `ai`; prefer these exact values.
- `conversationStart.initialPromptToUser` is present when trainee starts.
- `conversationDynamics.typicalBehaviors` and `possibleResponses` are non-empty.
- `conversationEndConditions.possibleEndStates` is non-empty.
- `evaluationCriteria` and `skillsAssessed` are non-empty.
- Criteria ids exactly match weighting keys; weights sum to 1.0.

For high-risk behavior, generate the live prompt locally and check that important behavior constraints appear in it:

```bash
PYTHONPATH=backend python - <<'PY'
from types import SimpleNamespace
from app.services.e2e_prompt_builder import build_e2e_system_prompt
# load or construct scenario as SimpleNamespace(
#   metadata=..., context=..., simulation_config=..., evaluation_config=...
# )
# print(build_e2e_system_prompt(scenario, "zh"))
PY
```

### 5. Store And Publish

Use the admin API. In the Docker/nginx setup, use `http://localhost/api/admin/scenarios`.

```bash
curl -s -X POST http://localhost/api/admin/scenarios \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -d @scenario.json
```

Then publish:

```bash
curl -s -X POST http://localhost/api/admin/scenarios/{id}/publish \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

Load `ADMIN_TOKEN` from `backend/.env` key `ADMIN_ACCESS_TOKEN`. Do not print secrets.

After publishing, verify:

- Public API can fetch `GET http://localhost/api/scenarios/{id}`.
- Generated prompt uses the intended bot name and language.
- Evaluation criteria count and weights are correct.

### 6. Iterate From Real Sessions

When the user reports bad behavior, inspect the session turns in MongoDB or the history page before editing. Diagnose which field caused the behavior:

- AI too cooperative: tighten `constraints`, `tendencies`, `decisionConstraints`, and remove cooperative `possibleResponses`.
- AI concedes too early: add thresholds, early-turn rules, concession ceilings, and "do not" rules.
- AI ignores key facts: move facts from `ai.knowledge` into injected fields.
- AI gives advice/coaching: strengthen roleplay-only constraints and remove coaching language from roleplay fields.
- Evaluation feels unfair: revise `evaluationInstructionsForLLM` and criterion descriptions.

Update the existing scenario through the admin `PUT` endpoint with `If-Match: {version}`. Preserve `status: "published"` unless the user asks to unpublish.

## References

- `references/scenario-schema.md`: field names, current prompt visibility, validation checklist.
- `references/scenario-design-patterns.md`: behavior-control strategy learned from successful scenarios and iterations.
- `references/example-teenage-son.json`: complete example of a layered resistant persona.
