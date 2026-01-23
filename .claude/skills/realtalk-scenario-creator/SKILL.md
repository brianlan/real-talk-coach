---
name: realtalk-scenario-creator
description: Generates communication training scenarios for Real Talk Coach. Use when you need to create a new practice scenario from a short description, including title, category, personas, objectives, end criteria, and skill mappings.
---

# Realtalk Scenario Creator

Creates complete communication training scenarios for the Real Talk Coach application. Takes a short scenario description and outputs a structured JSON with all required attributes for the scenario catalog.

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

**Language:** Generate scenario content (all JSON values) in the language the user uses. Keep JSON keys in English.

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
