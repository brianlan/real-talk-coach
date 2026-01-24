---
name: realtalk-scenario-creator
description: Generates communication training scenarios for Real Talk Coach. Use when you need to create a new practice scenario from a short description, including title, category, personas, objectives, end criteria, and skill mappings.
---

# Realtalk Scenario Creator

Creates complete communication training scenarios for the Real Talk Coach application. Takes a short scenario description and outputs a structured JSON with all required attributes for the scenario catalog.

## Workflow (Must Follow)

1) **Discuss first**: Before generating JSON, run a short discussion with the user to clarify ambiguities and propose improvements. Ask targeted questions until the scenario is well-defined.
2) **Language confirmation**: Confirm the preferred language for scenario content (JSON values). Do not assume; ask explicitly if unclear.
3) **Generate JSON**: Produce the scenario JSON with English keys and values in the confirmed language.
4) **Save to `./scenario.json`**:
   - If `./scenario.json` already exists, warn the user and ask for overwrite confirmation.
   - Only write the file after the user explicitly confirms overwrite (or if the file does not exist).
5) **Insert into DB**:
   - Call `backend/scripts/insert_scenario.py` using `PYTHONPATH` and loading `.env`.
   - Example invocation: `set -a; source backend/.env; set +a; PYTHONPATH=backend python backend/scripts/insert_scenario.py --file ./scenario.json`
   - Report success with `objectId` and timestamps if returned.

## Input Format

A brief description of the scenario to create, e.g.:
- "An employee asking for a raise"
- "Dealing with an angry customer who wants a refund"
- "Giving feedback to a colleague who constantly interrupts"

## Output Format

Returns a JSON object with:

| Field | Type | Description |
|-------|------|-------------|
| title | string | Scenario title (<= 120 chars) |
| category | string | Scenario category |
| description | string | Markdown narrative |
| objective | string | Success criteria text |
| aiPersona | object | {name, role, background} |
| traineePersona | object | {name: "You", role, background} |
| endCriteria | array[string] | 2-3 measurable stop conditions |
| requiredCommunicationSkills | array[string] | Skill IDs |

**Language:** Confirm with the user which language to use for scenario content (all JSON values). Keep JSON keys in English.

## Discussion Example

**User:** “我要一个关于管理中信任受损的场景。”

**Assistant:** “明白。为避免模糊，我先确认几件事并给出可选优化建议。”

**Questions:**
1) 你希望分类到 **Leadership** 还是 **Difficult Conversation**？
2) 对话发生在什么背景压力下？（比如关键客户、合规、事故、裁员后资源紧张）
3) 具体哪些行为导致对方感到不被信任？（选 1–2 个）
4) 对方的具体角色与层级？
5) 成功标准里是否需要“达成后续协作方式/检查频率”的条款？

**Suggestions:**
- 建议将压力来源具体化（比如关键客户上线节点），这样“收紧控制”更合理。
- 可加入 1–2 个“可观察行为”，让评价更客观（如每日同步、逐行 review）。

**Language Confirmation:**
- “你希望场景内容用中文还是英文？（JSON key 仍为英文）”

## Category Taxonomy

Use these categories appropriately:

| Category | Use For |
|----------|---------|
| Difficult Feedback | Delivering critical or constructive feedback |
| Conflict Resolution | Mediating disputes, handling disagreements |
| Negotiation | Bargaining, discussing terms |
| Difficult Conversation | Tough topics like raises, promotions |
| Leadership | Managing, motivating, guiding teams |
| Sales | Persuading, handling objections, closing |
| Customer Service | Complaints, support, issue resolution |
| Performance Review | Formal evaluations, appraisals |
| Apologizing | Making amends, taking responsibility |
| Declining Requests | Saying no professionally |

## Communication Skills Library

Map scenarios to these skill IDs:

| Skill ID | Name | Category |
|----------|------|----------|
| skill_active_listening | Active Listening | Feedback |
| skill_clear_ask | Clear Ask | Negotiation |

Select skills that align with the scenario type. Use multiple skills for complex scenarios.

## Persona Guidelines

**AI Persona:**
- name: Short, common name (Alex, Jordan, Sam)
- role: Job title relevant to scenario context
- background: Include emotional state/personality that creates appropriate tension

**Trainee Persona:**
- name: Always "You"
- role: Position that justifies initiating the conversation
- background: Responsibilities that make this conversation relevant

## End Criteria Guidelines

Create 2-3 specific, measurable criteria that:
1. Address the main issue being discussed
2. Define what resolution or agreement looks like
3. Are checkable by an objective evaluation model

## Description Guidelines

Write from a **3rd party narrative perspective**, not "You are...". Describe the scenario situation objectively.

**Bad:** "You are a team manager..."
**Good:** "The trainee plays the role of an engineering manager..."

## Example

**Input:** "A manager conducting a performance review for an underperforming employee"

**Output:**
```json
{
  "title": "Conduct a performance review with an underperforming team member",
  "category": "Performance Review",
  "description": "The trainee plays the role of an engineering manager conducting a quarterly review with their team member Jamie. Over the past quarter, Jamie has been missing deadlines and the quality of their work has declined. The goal is to address these issues while maintaining motivation and reaching an agreement on a performance improvement plan.",
  "objective": "Address the performance issues clearly while maintaining motivation, and agree on a performance improvement plan.",
  "aiPersona": {
    "name": "Jamie",
    "role": "Software Engineer",
    "background": "Has been at the company for 2 years. Recently went through a breakup and has been distracted. Defensive about criticism but wants to keep their job."
  },
  "traineePersona": {
    "name": "You",
    "role": "Engineering Manager",
    "background": "Responsible for team performance and development. Want to help Jamie succeed but also need to address the issues formally."
  },
  "endCriteria": [
    "Trainee clearly addresses specific performance issues with examples",
    "Trainee explores root cause and shows empathy",
    "Both parties agree on a concrete action plan with follow-up"
  ],
  "requiredCommunicationSkills": ["skill_active_listening", "skill_clear_ask"]
}
```
