import logging
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from app.storage.base import BaseStorage
from app.models.schemas import IPEntry, AuditEntry, IPStatus, PipelineStatus

logger = logging.getLogger(__name__)


class MongoDBStorage(BaseStorage):

    def __init__(self, uri: str, db_name: str = "ip_manager"):
        self._client = AsyncIOMotorClient(uri)
        self._db = self._client[db_name]
        self._ips = self._db["ips"]
        self._audits = self._db["audits"]
        self._locks = self._db["locks"]
        logger.info(f"MongoDB storage: connected to {db_name}")

    async def add_ip(self, entry: IPEntry) -> None:
        data = entry.model_dump()
        data["_id"] = entry.ip
        data["created_at"] = data["created_at"].isoformat()
        if data["expires_at"]:
            data["expires_at"] = data["expires_at"].isoformat()
        await self._ips.replace_one({"_id": entry.ip}, data, upsert=True)

    async def get_ip(self, ip: str) -> IPEntry | None:
        doc = await self._ips.find_one({"_id": ip})
        if not doc:
            return None
        return self._to_entry(doc)

    async def list_ips(self, status: IPStatus | None = None) -> list[IPEntry]:
        query = {"status": status.value} if status else {}
        entries = []
        async for doc in self._ips.find(query).sort("created_at", -1):
            entries.append(self._to_entry(doc))
        return entries

    async def update_ip_status(self, ip: str, status: IPStatus) -> bool:
        result = await self._ips.update_one(
            {"_id": ip}, {"$set": {"status": status.value}}
        )
        return result.matched_count > 0

    async def remove_ip(self, ip: str) -> bool:
        result = await self._ips.delete_one({"_id": ip})
        return result.deleted_count > 0

    async def get_active_ips(self) -> list[IPEntry]:
        return await self.list_ips(status=IPStatus.ACTIVE)

    async def add_audit(self, entry: AuditEntry) -> None:
        data = entry.model_dump()
        data["timestamp"] = data["timestamp"].isoformat()
        data["_id"] = f"{entry.timestamp.strftime('%Y%m%d%H%M%S%f')}_{entry.ip}"
        await self._audits.insert_one(data)

    async def list_audits(self, limit: int = 100) -> list[AuditEntry]:
        entries = []
        async for doc in self._audits.find().sort("timestamp", -1).limit(limit):
            doc["timestamp"] = datetime.fromisoformat(doc["timestamp"])
            doc.pop("_id", None)
            entries.append(AuditEntry(**doc))
        return entries

    async def update_pipeline_status(self, ip: str, status: PipelineStatus) -> bool:
        result = await self._ips.update_one(
            {"_id": ip}, {"$set": {"pipeline_status": status.value}}
        )
        return result.matched_count > 0

    async def bulk_update_pipeline_status(
        self, from_status: PipelineStatus, to_status: PipelineStatus
    ) -> int:
        result = await self._ips.update_many(
            {"pipeline_status": from_status.value},
            {"$set": {"pipeline_status": to_status.value}}
        )
        return result.modified_count

    async def try_lock(self, lock_id: str, ttl_seconds: int = 60) -> bool:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=ttl_seconds)
        try:
            result = await self._locks.update_one(
                {
                    "_id": lock_id,
                    "$or": [
                        {"expires": {"$lte": now.isoformat()}},
                        {"expires": {"$exists": False}},
                    ]
                },
                {"$set": {"acquired_at": now.isoformat(), "expires": expires.isoformat()}},
                upsert=False,
            )
            if result.matched_count > 0:
                return True
            try:
                await self._locks.insert_one({
                    "_id": lock_id,
                    "acquired_at": now.isoformat(),
                    "expires": expires.isoformat(),
                })
                return True
            except Exception:
                return False
        except Exception as e:
            logger.error(f"Lock error for {lock_id}: {e}")
            return False

    async def release_lock(self, lock_id: str) -> None:
        try:
            await self._locks.delete_one({"_id": lock_id})
        except Exception as e:
            logger.error(f"Lock release error for {lock_id}: {e}")

    @staticmethod
    def _to_entry(doc: dict) -> IPEntry:
        doc.pop("_id", None)
        if isinstance(doc.get("created_at"), str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc.get("expires_at"), str):
            doc["expires_at"] = datetime.fromisoformat(doc["expires_at"])
        # Backcompat: old docs won't have pipeline_status
        if "pipeline_status" not in doc:
            doc["pipeline_status"] = "applied"
        return IPEntry(**doc)
