#!/usr/bin/env python3
"""
Migration script to import data from LeanCloud to MongoDB.

Usage:
    python scripts/migrate_from_leancloud.py --dry-run
    python scripts/migrate_from_leancloud.py
"""

import argparse
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from pymongo import AsyncMongoClient


class MigrationRunner:
    """Handles migration from LeanCloud to MongoDB."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.leancloud_base_url = os.getenv("LEAN_SERVER_URL", "https://api.leancloud.cn")
        self.leancloud_app_id = os.getenv("LEAN_APP_ID")
        self.leancloud_app_key = os.getenv("LEAN_APP_KEY")
        self.leancloud_master_key = os.getenv("LEAN_MASTER_KEY")
        
        # MongoDB connection
        mongo_host = os.getenv("MONGO_HOST", "localhost")
        mongo_port = int(os.getenv("MONGO_PORT", "27017"))
        mongo_db = os.getenv("MONGO_DB", "real-talk-coach")
        self.mongo_uri = f"mongodb://{mongo_host}:{mongo_port}"
        self.mongo_db_name = mongo_db
        
        self.mongo_client = None
        self.http_client = None
        self.stats = {
            "PracticeSession": {"scanned": 0, "migrated": 0},
            "Turn": {"scanned": 0, "migrated": 0},
            "Scenario": {"scanned": 0, "migrated": 0},
            "Skill": {"scanned": 0, "migrated": 0},
            "Evaluation": {"scanned": 0, "migrated": 0},
            "AuditLog": {"scanned": 0, "migrated": 0},
        }
    
    async def connect(self):
        """Connect to MongoDB and LeanCloud."""
        print(f"Connecting to MongoDB at {self.mongo_uri}...")
        self.mongo_client = AsyncMongoClient(self.mongo_uri)
        self.db = self.mongo_client[self.mongo_db_name]
        print(f"Connected to MongoDB: {self.mongo_db_name}")
        
        # Create HTTP client for LeanCloud
        self.http_client = httpx.AsyncClient(
            base_url=self.leancloud_base_url,
            headers={
                "X-LC-Id": self.leancloud_app_id,
                "X-LC-Key": self.leancloud_master_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        print(f"Connected to LeanCloud: {self.leancloud_base_url}")
    
    async def close(self):
        """Close connections."""
        if self.mongo_client:
            await self.mongo_client.aclose()
        if self.http_client:
            await self.http_client.aclose()
    
    async def fetch_leancloud_collection(self, collection_name: str, limit: int = 1000) -> list:
        """Fetch all records from a LeanCloud collection."""
        url = f"/1.1/classes/{collection_name}"
        records = []
        skip = 0
        
        while True:
            try:
                params = {"limit": limit, "skip": skip}
                response = await self.http_client.get(url, params=params)
                if response.status_code != 200:
                    print(f"Error fetching {collection_name}: {response.status_code} {response.text}")
                    break
                
                data = response.json()
                results = data.get("results", [])
                if not results:
                    break
                    
                records.extend(results)
                print(f"  Fetched {len(results)} records (total: {len(records)})")
                
                if len(results) < limit:
                    break
                    
                skip += limit
                
            except Exception as e:
                print(f"Error fetching {collection_name}: {e}")
                break
        
        return records
    
    async def migrate_collection(self, collection_name: str, transform_func):
        """Migrate a single collection."""
        print(f"\n--- Migrating {collection_name} ---")
        
        # Fetch from LeanCloud
        records = await self.fetch_leancloud_collection(collection_name)
        self.stats[collection_name]["scanned"] = len(records)
        print(f"Found {len(records)} records in LeanCloud")
        
        if not records:
            print("Migrated: 0")
            return
        
        if self.dry_run:
            print(f"[DRY RUN] Would migrate {len(records)} records")
            return
        
        # Get MongoDB collection
        collection = self.db[collection_name]
        
        # Transform and insert
        migrated = 0
        for record in records:
            try:
                transformed = transform_func(record)
                # Remove None values
                transformed = {k: v for k, v in transformed.items() if v is not None}
                await collection.insert_one(transformed)
                migrated += 1
            except Exception as e:
                print(f"Error migrating record: {e}")
        
        self.stats[collection_name]["migrated"] = migrated
        print(f"Migrated: {migrated}")
    
    def transform_session(self, lc_record: dict) -> dict:
        """Transform LeanCloud PracticeSession to MongoDB format."""
        return {
            "_id": lc_record.get("objectId"),
            "scenario_id": lc_record.get("scenarioId"),
            "stub_user_id": lc_record.get("stubUserId"),
            "status": lc_record.get("status", "active"),
            "started_at": lc_record.get("createdAt"),
            "ended_at": lc_record.get("endedAt"),
            "termination_reason": lc_record.get("terminationReason"),
            "objective_status": lc_record.get("objectiveStatus"),
        }
    
    def transform_turn(self, lc_record: dict) -> dict:
        """Transform LeanCloud Turn to MongoDB format."""
        return {
            "_id": lc_record.get("objectId"),
            "session_id": lc_record.get("sessionId"),
            "turn_index": lc_record.get("turnIndex"),
            "role": lc_record.get("role"),
            "content": lc_record.get("content"),
            "audio_url": lc_record.get("audioUrl"),
            "created_at": lc_record.get("createdAt"),
        }
    
    def transform_scenario(self, lc_record: dict) -> dict:
        """Transform LeanCloud Scenario to MongoDB format."""
        return {
            "_id": lc_record.get("objectId"),
            "title": lc_record.get("title"),
            "description": lc_record.get("description"),
            "prompt": lc_record.get("prompt"),
            "status": lc_record.get("recordStatus", "published"),
            "created_at": lc_record.get("createdAt"),
            "updated_at": lc_record.get("updatedAt"),
        }
    
    def transform_skill(self, lc_record: dict) -> dict:
        """Transform LeanCloud Skill to MongoDB format."""
        return {
            "_id": lc_record.get("objectId"),
            "name": lc_record.get("name"),
            "description": lc_record.get("description"),
            "status": lc_record.get("status", "active"),
            "created_at": lc_record.get("createdAt"),
            "updated_at": lc_record.get("updatedAt"),
        }
    
    def transform_evaluation(self, lc_record: dict) -> dict:
        """Transform LeanCloud Evaluation to MongoDB format."""
        return {
            "_id": lc_record.get("objectId"),
            "session_id": lc_record.get("sessionId"),
            "scores": lc_record.get("scores", []),
            "summary": lc_record.get("summary"),
            "created_at": lc_record.get("createdAt"),
        }
    
    def transform_audit_log(self, lc_record: dict) -> dict:
        """Transform LeanCloud AuditLog to MongoDB format."""
        return {
            "_id": lc_record.get("objectId"),
            "admin_id": lc_record.get("adminId"),
            "action": lc_record.get("action"),
            "entity_type": lc_record.get("entityType"),
            "entity_id": lc_record.get("entityId"),
            "details": lc_record.get("details"),
            "created_at": lc_record.get("createdAt"),
        }
    
    async def run(self):
        """Run the migration."""
        print("=" * 50)
        print("LeanCloud to MongoDB Migration")
        print("=" * 50)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"LeanCloud URL: {self.leancloud_base_url}")
        print(f"MongoDB: {self.mongo_uri}/{self.mongo_db_name}")
        print("=" * 50)
        
        await self.connect()
        
        try:
            # Migrate each collection
            await self.migrate_collection("PracticeSession", self.transform_session)
            await self.migrate_collection("Turn", self.transform_turn)
            await self.migrate_collection("Scenario", self.transform_scenario)
            await self.migrate_collection("Skill", self.transform_skill)
            await self.migrate_collection("Evaluation", self.transform_evaluation)
            await self.migrate_collection("AuditLog", self.transform_audit_log)
            
            # Print summary
            print("\n" + "=" * 50)
            print("Migration Summary")
            print("=" * 50)
            for coll, stats in self.stats.items():
                print(f"{coll}: {stats['migrated']} migrated")
            
        finally:
            await self.close()
        
        print("\nMigration complete!")


def main():
    parser = argparse.ArgumentParser(description="Migrate data from LeanCloud to MongoDB")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually migrating"
    )
    args = parser.parse_args()
    
    runner = MigrationRunner(dry_run=args.dry_run)
    asyncio.run(runner.run())


if __name__ == "__main__":
    main()
