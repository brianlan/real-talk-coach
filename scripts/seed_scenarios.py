from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.append(str(BACKEND_ROOT))

from app.clients.leancloud import LeanCloudClient, LeanCloudError
from app.config import SettingsError, load_settings


def _read_json(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise ValueError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError(f"Expected a list in {path}")
    if not all(isinstance(item, dict) for item in data):
        raise ValueError(f"Expected a list of objects in {path}")
    return data


def _require_fields(item: dict[str, Any], fields: list[str], context: str) -> None:
    missing = [field for field in fields if not item.get(field)]
    if missing:
        raise ValueError(f"{context} missing required fields: {', '.join(missing)}")


def _validate_skill(skill: dict[str, Any]) -> None:
    _require_fields(skill, ["externalId", "name", "category", "rubric"], "Skill")


def _validate_scenario(scenario: dict[str, Any]) -> None:
    _require_fields(
        scenario,
        [
            "externalId",
            "category",
            "title",
            "description",
            "objective",
            "aiPersona",
            "traineePersona",
            "endCriteria",
            "skills",
            "prompt",
            "status",
        ],
        "Scenario",
    )
    if not isinstance(scenario.get("endCriteria"), list):
        raise ValueError("Scenario endCriteria must be a list")
    if not isinstance(scenario.get("skills"), list):
        raise ValueError("Scenario skills must be a list")


async def _fetch_by_external_id(
    client: LeanCloudClient, class_name: str, external_id: str
) -> dict[str, Any] | None:
    where = json.dumps({"externalId": external_id})
    response = await client.get_json(f"/1.1/classes/{class_name}", params={"where": where})
    results = response.get("results", [])
    if results:
        return results[0]
    return None


async def _ensure_class(client: LeanCloudClient, class_name: str) -> None:
    try:
        await client.post_json(f"/1.1/schemas/{class_name}", {"className": class_name})
    except LeanCloudError as exc:
        body = exc.body or ""
        if "exists" in body.lower():
            return
        if exc.status_code in {400, 404}:
            return
        raise


async def _upsert_skill(client: LeanCloudClient, skill: dict[str, Any]) -> str:
    existing = await _fetch_by_external_id(client, "Skill", skill["externalId"])
    payload = {
        "externalId": skill["externalId"],
        "name": skill["name"],
        "category": skill["category"],
        "rubric": skill["rubric"],
        "description": skill.get("description"),
    }
    if existing:
        object_id = existing["objectId"]
        await client.put_json(f"/1.1/classes/Skill/{object_id}", payload)
        return object_id
    response = await client.post_json("/1.1/classes/Skill", payload)
    return response["objectId"]


async def _upsert_scenario(
    client: LeanCloudClient,
    scenario: dict[str, Any],
    skill_map: dict[str, str],
) -> str:
    external_ids = scenario["skills"]
    missing = [skill for skill in external_ids if skill not in skill_map]
    if missing:
        raise ValueError(f"Scenario {scenario['externalId']} references unknown skills: {missing}")
    payload = {
        "externalId": scenario["externalId"],
        "category": scenario["category"],
        "title": scenario["title"],
        "description": scenario["description"],
        "objective": scenario["objective"],
        "aiPersona": scenario["aiPersona"],
        "traineePersona": scenario["traineePersona"],
        "endCriteria": scenario["endCriteria"],
        "skills": [skill_map[skill] for skill in external_ids],
        "idleLimitSeconds": scenario.get("idleLimitSeconds"),
        "durationLimitSeconds": scenario.get("durationLimitSeconds"),
        "prompt": scenario["prompt"],
        "status": scenario["status"],
    }
    existing = await _fetch_by_external_id(client, "Scenario", scenario["externalId"])
    if existing:
        object_id = existing["objectId"]
        await client.put_json(f"/1.1/classes/Scenario/{object_id}", payload)
        return object_id
    response = await client.post_json("/1.1/classes/Scenario", payload)
    return response["objectId"]


async def _run(skills_path: Path, scenarios_path: Path) -> int:
    skills = _read_json(skills_path)
    scenarios = _read_json(scenarios_path)

    for skill in skills:
        _validate_skill(skill)
    for scenario in scenarios:
        _validate_scenario(scenario)

    try:
        settings = load_settings()
    except SettingsError as exc:
        raise ValueError(str(exc)) from exc

    client = LeanCloudClient(
        app_id=settings.lean_app_id,
        app_key=settings.lean_app_key,
        master_key=settings.lean_master_key,
        server_url=settings.lean_server_url,
    )

    skill_map: dict[str, str] = {}
    try:
        await _ensure_class(client, "Skill")
        await _ensure_class(client, "Scenario")
        for skill in skills:
            object_id = await _upsert_skill(client, skill)
            skill_map[skill["externalId"]] = object_id

        for scenario in scenarios:
            await _upsert_scenario(client, scenario, skill_map)
    finally:
        await client.close()

    print(f"Seed complete: {len(skill_map)} skills, {len(scenarios)} scenarios")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed LeanCloud scenarios and skills")
    parser.add_argument("--skills", required=True, type=Path)
    parser.add_argument("--scenarios", required=True, type=Path)
    args = parser.parse_args()

    try:
        return asyncio.run(_run(args.skills, args.scenarios))
    except Exception as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
