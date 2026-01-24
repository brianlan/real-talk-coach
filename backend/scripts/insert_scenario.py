#!/usr/bin/env python3
"""
Insert a scenario into LeanCloud database.

Usage:
    python insert_scenario.py <scenario.json
    python insert_scenario.py --file scenario.json
    echo '{"title": "..."}' | python insert_scenario.py

Environment variables (required):
    LEAN_APP_ID      - LeanCloud App ID
    LEAN_APP_KEY     - LeanCloud App Key
    LEAN_MASTER_KEY  - LeanCloud Master Key
    LEAN_SERVER_URL  - LeanCloud Server URL

Environment file support:
    The script automatically loads .env from the current directory or parent directories.
    Environment variables from .env are loaded first, then can be overridden by shell exports.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from app.clients.leancloud import LeanCloudClient


def load_dotenv(dotenv_path: str | None = None) -> None:
    """Load environment variables from a .env file.

    Args:
        dotenv_path: Path to .env file. If None, looks for .env in current directory.
    """
    if dotenv_path is None:
        candidates = [Path(".env"), Path("../.env"), Path("../../.env")]
        for candidate in candidates:
            if candidate.exists():
                dotenv_path = str(candidate)
                break

    if dotenv_path and Path(dotenv_path).exists():
        with open(dotenv_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Only set if not already in environment
                if key and value and key not in os.environ:
                    os.environ[key] = value


async def create_scenario(client: LeanCloudClient, payload: dict[str, Any]) -> dict[str, Any]:
    """Create a scenario in LeanCloud and return the created record."""
    data = {"recordStatus": "active", **payload}
    response = await client.post_json("/1.1/classes/Scenario", data)
    record = data | response
    return record


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize the scenario payload to match LeanCloud field names."""
    # Map snake_case keys to camelCase for LeanCloud
    mapping = {
        "aiPersona": "aiPersona",
        "traineePersona": "traineePersona",
        "endCriteria": "endCriteria",
        "requiredCommunicationSkills": "skills",
    }

    normalized = {}
    for lc_key, input_key in mapping.items():
        if input_key in payload:
            normalized[lc_key] = payload[input_key]

    # Copy other fields directly
    for key in ["title", "category", "description", "objective", "prompt"]:
        if key in payload:
            normalized[key] = payload[key]

    # Set defaults if not provided
    normalized.setdefault("status", "draft")
    normalized.setdefault("idleLimitSeconds", 8)
    normalized.setdefault("durationLimitSeconds", 300)

    return normalized


async def main() -> None:
    # Load scenario from stdin or file
    if len(sys.argv) > 1 and sys.argv[1] == "--file":
        if len(sys.argv) < 3:
            print("Error: --file requires a file path", file=sys.stderr)
            sys.exit(1)
        with open(sys.argv[2], encoding="utf-8") as f:
            payload = json.load(f)
    else:
        input_data = sys.stdin.read()
        if not input_data.strip():
            print("Error: No input provided. Pipe JSON or use --file", file=sys.stderr)
            sys.exit(1)
        payload = json.loads(input_data)

    # Normalize field names
    normalized = normalize_payload(payload)

    # Initialize LeanCloud client
    # Load .env file first (looks for .env in current dir or parent dirs)
    load_dotenv()

    app_id = "LEAN_APP_ID"
    app_key = "LEAN_APP_KEY"
    master_key = "LEAN_MASTER_KEY"
    server_url = "LEAN_SERVER_URL"

    # Override with environment variables if set
    if os.environ.get("LEAN_APP_ID"):
        app_id = os.environ["LEAN_APP_ID"]
    if os.environ.get("LEAN_APP_KEY"):
        app_key = os.environ["LEAN_APP_KEY"]
    if os.environ.get("LEAN_MASTER_KEY"):
        master_key = os.environ["LEAN_MASTER_KEY"]
    if os.environ.get("LEAN_SERVER_URL"):
        server_url = os.environ["LEAN_SERVER_URL"]
    else:
        server_url = "https://YOUR_APP.leancloud.cn"

    client = LeanCloudClient(
        app_id=app_id,
        app_key=app_key,
        master_key=master_key,
        server_url=server_url,
    )

    # Create the scenario
    result = await create_scenario(client, normalized)

    # Print result
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
