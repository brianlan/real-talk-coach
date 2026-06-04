---
name: realtalk-scenario-creator
description: >
  Creates complete, production-ready practice scenarios for the Real Talk Coach application.
  Use this skill whenever the user wants to create a new conversation practice scenario,
  design a roleplay simulation, add a practice topic, or describes a communication situation
  they want to turn into a trainable exercise. Also trigger when the user mentions scenarios,
  roleplay personas, conversation simulations, communication training topics, or asks about
  what practice scenarios exist in the system. This skill handles the complete lifecycle:
  gathering requirements from the user, designing the scenario JSON, validating it against
  the system's prompt builder and evaluator, and storing it in the database.
---

# Real Talk Coach — Scenario Creator

You create conversation practice scenarios for the Real Talk Coach platform. Each scenario defines a complete roleplay simulation: who the AI pretends to be, who the trainee is, what the situation is, how the AI should behave, and how the trainee's performance gets evaluated.

## Architecture Overview

The system has two distinct AI pipelines that consume different parts of a scenario:

1. **Roleplay Prompt Builder** (`e2e_prompt_builder.py`) — Builds the system prompt sent to the voice AI. It reads `simulationConfig` and `context` to construct the AI's personality, behavior rules, and conversation dynamics. It explicitly does NOT see evaluation criteria (so the AI can't accidentally coach the trainee).

2. **Evaluation Pipeline** (`evaluation_service.py`) — After practice ends, sends the transcript + `evaluationConfig` to an LLM evaluator that scores the trainee against defined criteria.

Understanding this split is essential because it determines what information goes where — and what the AI character genuinely does not know about.

## Workflow

### Phase 1: Gather Requirements

Before writing any JSON, have a conversation with the user. Your goal is to understand the human situation deeply enough to create a realistic simulation. Ask about these dimensions:

**Essential information (must get answers to all of these):**

1. **Topic** — What conversation does the user want to practice? (e.g., "ask for a raise", "talk to my rebellious teenager", "deliver bad news to a team")

2. **Who the AI should roleplay** — Not just a job title, but their personality, emotional state, and what makes them tick. The richer the characterization, the more realistic the simulation.

3. **Who the trainee is** — Their role and what they're trying to achieve. This shapes the evaluation criteria.

4. **The core tension** — What makes this conversation difficult? What's the gap between what the trainee wants and what the AI character is inclined to give?

5. **What success looks like** — Not just "they reach an agreement" but the specific communication skills the trainee should demonstrate. This becomes your evaluation criteria.

6. **Language** — Should the scenario content be in English or Chinese? (The `language` field and content values should match.)

**Enrichment questions (ask when the user's initial description is thin):**

7. What are the AI character's hidden motivations or constraints? (Things they won't say out loud but that drive their behavior)
8. What topics or behaviors would make the AI character shut down or get defensive?
9. Are there safe topics the trainee can use to build rapport before tackling the hard stuff?
10. What does a partial success look like? (In many scenarios, a full resolution in one conversation is unrealistic)

You don't need to ask all of these as a numbered list. Weave them into a natural conversation. The point is to get enough material to create a persona with depth and a situation with genuine tension.

### Phase 2: Design the Scenario

Read `references/scenario-schema.md` for the complete field reference. Below are the design principles that make the difference between a flat scenario and one that produces realistic, useful practice.

#### Designing the AI Persona (`simulationConfig.ai`)

The AI persona is the heart of the scenario. The prompt builder reads these fields directly and injects them into the system prompt:

- **`personality`** — Surface traits everyone can see. Keep these to 3-5 adjectives or short phrases.
- **`motivations`** — What drives the character underneath. This shapes behavior the trainee can sense but can't directly see. 3-4 items.
- **`constraints`** — External or internal limits on what the character can do. These create the walls the trainee has to navigate. 3-4 items.
- **`tendencies`** — The behavioral engine. This is the most important field. Write each tendency as a specific behavioral pattern with a trigger condition. The prompt builder puts these front and center in the "REALISTIC BEHAVIOR" section. 5-7 items is ideal. Example: *"gives short, dismissive answers like 'fine', 'whatever', 'I don't know' when asked about school or feelings"*
- **`knowledge`** — What the character knows going into the conversation. This frames their perspective. Include both what they know and what they don't know.
- **`emotionalState`** — A short phrase describing their mood. The prompt builder puts this in a dedicated line.

**The Layered Persona technique:** The best scenarios give the AI character a surface behavior and a hidden truth. Surface: "guarded, sarcastic, dismissive." Hidden: "secretly lonely and longing for someone who genuinely gets him." This creates depth because the trainee can sense there's something underneath but has to work to reach it. The AI won't volunteer the hidden truth — it only emerges through patient, skilled communication.

#### Designing Conversation Dynamics (`simulationConfig.conversationDynamics`)

- **`typicalBehaviors`** — What the AI typically does in this conversation. Write these as behavioral patterns, not dialogue. 4-5 items.
- **`possibleResponses`** — Actual dialogue snippets the AI might use. These serve as a vocabulary for the AI — concrete examples of how to respond. Include a mix: some deflecting, some revealing, some neutral. 6-8 items is ideal. Example: *"School's just... whatever. Some people there are just... nah, forget it."*

#### Designing Decision Constraints (`simulationConfig.decisionConstraints`)

This is a free-form JSON object that gets rendered as bullet points. Use it to encode the "game rules" — the conditions that govern the AI's behavior. Good things to include:

- **Openness/shutdown thresholds** — How many times will the AI deflect before showing vulnerability?
- **Safe topics for connection** — Topics the AI will engage with happily (building rapport)
- **Triggers for shutdown** — Behaviors that make the AI close up (lecturing, comparing, criticizing)
- **Path to resolution** — The staged progression the AI follows (rapport → openness → hint → validation → reveal)

#### Designing the Evaluation (`evaluationConfig`)

The evaluator LLM receives: scenario title, context, learning objectives, evaluation criteria (with IDs), skills assessed, scoring config, custom instructions, and the full conversation transcript.

**Writing good evaluation criteria:**

Each criterion has an `id` (snake_case) and a `description` (what to look for). Write descriptions that an LLM can score objectively — specific behaviors or outcomes, not vague qualities.

Good: *"Parent initiates conversation casually, without jumping straight to serious topics like grades or school. Approaches like a real moment, not an intervention."*
Bad: *"Parent has good communication skills."*

**Setting realistic expectations in `evaluationInstructionsForLLM`:**

This field is your control valve for the evaluator. Use it to:
- Define what "good enough" looks like (not just "perfect")
- Clarify that partial progress counts as success where appropriate
- Prevent overly harsh scoring by explaining the scenario's inherent difficulty
- Direct the evaluator's attention to what matters most

Example: *"The goal is NOT to get the son to fully confess his problems — that is unrealistic in a single conversation. Even a small moment of genuine connection is a meaningful outcome."*

**Criteria-weight alignment:** Every `evaluationCriteria[].id` must appear as a key in `scoring.criteriaWeighting`. Weights should sum to approximately 1.0.

### Phase 3: Validate

Before storing, verify the scenario passes all checks:

1. All four top-level sections present: `metadata`, `context`, `simulationConfig`, `evaluationConfig`
2. `simulationConfig.ai` has all sub-fields: `name`, `role`, `personality`, `motivations`, `constraints`, `tendencies`, `knowledge`, `emotionalState`
3. `simulationConfig.trainee` has the same sub-fields
4. `simulationConfig.conversationStart` has `speakerRoleId` and `initialPromptToUser`
5. `evaluationConfig.evaluationCriteria` is a non-empty array
6. `evaluationConfig.skillsAssessed` is a non-empty array
7. All `evaluationCriteria[].id` values match keys in `scoring.criteriaWeighting`
8. `scoring.criteriaWeighting` values sum to approximately 1.0
9. `conversationStart.speakerRoleId` uses a recognizable role ("trainee" starts the conversation, or "ai" for the AI to start)

Read `references/scenario-schema.md` for the complete validation checklist and field mapping.

### Phase 4: Store in Database

Store the scenario via the admin API:

```bash
curl -s -X POST http://localhost:8000/api/admin/scenarios \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -d @scenario.json
```

The admin token is in `backend/.env` as `ADMIN_ACCESS_TOKEN`. The API returns the created scenario with its `id`.

After creation, publish it:

```bash
curl -s -X POST http://localhost:8000/api/admin/scenarios/{id}/publish \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

Alternatively, use the seed script (loads `.env` automatically):

```bash
set -a; source backend/.env; set +a
PYTHONPATH=backend python backend/scripts/seed_scenarios.py --single-scenario ./scenario.json
```

### Phase 5: Present and Iterate

Show the user the created scenario with:
- Title and ID
- AI persona summary (name, role, key traits)
- Trainee persona summary
- Number of evaluation criteria
- Validation status

Ask the user to try it in the app and report back. Common iteration points:
- AI is too easy to convince → strengthen `constraints` and `tendencies`
- AI opens up too quickly → increase deflection threshold in `decisionConstraints`
- Evaluation feels wrong → adjust `evaluationInstructionsForLLM` or refine criteria descriptions
- Conversation feels flat → add more specific `possibleResponses` dialogue snippets

## Reference Files

- **`references/scenario-schema.md`** — Complete field-by-field reference with types, which pipeline reads each field, and the validation checklist. Read this when you need to confirm exact field names or understand the prompt builder mapping.
- **`references/example-teenage-son.json`** — A complete worked example: the "Connect with Your Teenage Son" scenario. Read this when you want to see how the design principles translate into concrete JSON. It demonstrates the layered persona technique, rich decision constraints, and realistic evaluation expectations.
