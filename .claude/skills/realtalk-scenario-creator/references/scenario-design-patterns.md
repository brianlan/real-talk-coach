# Scenario Design Patterns

Use these patterns when designing or tuning realistic Real Talk Coach scenarios.

## Core Principle

The roleplay AI tends to be helpful and cooperative unless the scenario explicitly controls pacing. For difficult conversations, design a response rhythm, not just a persona.

Strong behavior controls live in:

- `ai.constraints`
- `ai.tendencies`
- `conversationDynamics.typicalBehaviors`
- `conversationDynamics.possibleResponses`
- `decisionConstraints`

Weak or non-live controls:

- `ai.knowledge` is stored but not injected into the current roleplay prompt.
- `evaluationConfig` does not affect live roleplay.
- Vague adjectives like "defensive" are weaker than turn-by-turn rules.

## Resistant Persona Recipe

For any AI character who should not cooperate immediately, define:

```json
"decisionConstraints": {
  "initialAwareness": "...",
  "admissionThreshold": "...",
  "earlyTurnRule": [
    "前几轮不要主动完整认错",
    "不要主动提出完整解决方案",
    "先表现为困惑、拖延、最小化、解释或转移话题"
  ],
  "defaultDeflectionPattern": [
    "first deflection",
    "second deflection",
    "third deflection",
    "only then partial concession"
  ],
  "agreementPacing": "...",
  "doNotMakeAI": [
    "不要一开始就全面认错",
    "不要主动提出完美计划",
    "不要突然高度自省"
  ]
}
```

Use concrete thresholds: "after 3-5 deflections", "after the trainee names 2-3 specific facts", "only after the trainee asks for a written plan".

## Concession Ceilings

If money, responsibility, confession, apology, vulnerability, or agreement is involved, define what the AI may concede early.

Bad:

```json
"reasonableAgreementOptions": ["先还一部分"]
```

Better:

```json
"hardPaymentCeiling": "前3-5轮不得主动承诺10万、15万或接近全额的大额还款。",
"emergencyPressureRule": [
  "家人生病只触发关心和小额应急姿态",
  "早期可主动提出5000到2万元，最高3万元",
  "更大金额继续绑定到不确定回款，不给可靠大额日期"
]
```

The model may inflate vague phrases like "一部分" into a large concession. Give explicit ceilings.

## Emergency Or Moral Pressure

User messages like "my father is sick", "I urgently need money", "this hurt me badly", or "you are ruining my life" can make the AI overly helpful. If the persona should still resist, add a special rule:

- The AI should show concern.
- The AI may offer resources, sympathy, or a small immediate action.
- The AI must not jump to full responsibility or a large commitment.
- The AI should still protect its incentive/persona.

Example:

```json
"emergencyPressureRule": [
  "如果用户提到家人生病，小周要表现关心，但不要马上承诺10万或接近全额还款",
  "优先回应为问候病情、提供人脉资源、说自己想办法挪一点点应急",
  "只有用户连续追问还款计划并要求书面确认，才讨论更完整分期"
]
```

## Possible Responses Are Behavioral Anchors

The model copies the cooperation level implied by `possibleResponses`.

Avoid lines like:

- "你说得对，都是我的问题。"
- "我下周先还你10万。"
- "我马上做一个完整计划。"
- "我完全理解，我会改。"

Prefer lines matching the intended phase:

- "有这么严重吗？我以为只是有点乱。"
- "我不是不还，最近就是手头倒不开。"
- "要不我先想办法挪一点点给你应急？"
- "如果你非要写下来，那是不是有点伤感情？"

Include a few partial-concession snippets, but cap them and place them late in the progression.

## Agreement Pacing

Do not write only the final happy path. Write the sequence:

1. Initial confusion/deflection.
2. Minimization or emotional pressure.
3. User gives concrete facts and impact.
4. AI concedes one specific point.
5. User asks for concrete next step.
6. AI accepts a limited, imperfect action.
7. User confirms follow-up.

If the AI should be hard, the first concrete concession should be small and imperfect.

## Evaluation Strategy

Evaluate the trainee's communication skill, not whether the AI becomes ideal.

For resistant scenarios, `evaluationInstructionsForLLM` should say:

- The AI is expected to resist.
- Full resolution is unrealistic in one conversation.
- Partial progress can be success.
- Score the trainee on opening, specificity, boundary clarity, handling deflection, and follow-through.
- Do not require the AI to fully confess, repay, clean, apologize, or change.

## Useful Criteria Templates

Use 5-6 criteria. Adapt names to the scenario.

```json
[
  {
    "id": "respectful_direct_opening",
    "description": "Trainee opens directly and respectfully, without avoidance or attack."
  },
  {
    "id": "specific_facts_and_impact",
    "description": "Trainee names concrete facts and real impact instead of vague blame."
  },
  {
    "id": "separating_person_from_problem",
    "description": "Trainee distinguishes the person/relationship from the problematic behavior."
  },
  {
    "id": "clear_boundaries_and_requests",
    "description": "Trainee asks for specific actions, timing, and follow-up."
  },
  {
    "id": "handling_deflection",
    "description": "Trainee handles minimization, delay, emotional pressure, or topic shifts without losing the thread."
  },
  {
    "id": "collaborative_follow_through",
    "description": "Trainee confirms next steps and keeps the conversation constructive."
  }
]
```

## Debugging Bad Roleplay

When a user reports bad behavior, inspect the actual transcript and map it back to scenario fields.

If the AI concedes too early:

- Remove or rewrite cooperative `possibleResponses`.
- Add `earlyTurnRule`.
- Add `admissionThreshold` or `repaymentCommitmentThreshold`.
- Add `hardPaymentCeiling`, `vulnerabilityThreshold`, or equivalent.
- Add "not enough" cases, such as emergency pressure not being enough for a large concession.

If the AI ignores hidden facts:

- Move facts from `ai.knowledge` into `context`, `constraints`, `tendencies`, or `decisionConstraints`.

If the AI is too hostile:

- Add safe paths to partial agreement.
- Add triggers that make the AI soften.
- Include small, realistic concessions.

If evaluation is harsh:

- Clarify partial success in `evaluationInstructionsForLLM`.
- Make criteria observable and transcript-based.
