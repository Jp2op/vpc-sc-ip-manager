import logging
from google.cloud import firestore
from app.storage.base import BaseStorage
from app.models.schemas import IPEntry, AuditEntry, IPStatus, PipelineStatus
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class FirestoreStorage(BaseStorage):

    def __init__(self, project_id: str, collection: str = "ip_whitelist"):
        self._db = firestore.AsyncClient(project=project_id)
        self._col = collection

    @property
    def _ips_ref(self):
        return self._db.collection(self._col).document("data").collection("ips")

    @property
    def _audits_ref(self):
        return self._db.collection(self._col).document("data").collection("audits")

    @property
    def _locks_ref(self):
        return self._db.collection(self._col).document("data").collection("locks")

    async def add_ip(self, entry: IPEntry) -> None:
        data = entry.model_dump()
        data["created_at"] = data["created_at"].isoformat()
        if data["expires_at"]:
            data["expires_at"] = data["expires_at"].isoformat()
        await self._ips_ref.document(entry.ip).set(data)

    async def get_ip(self, ip: str) -> IPEntry | None:
        doc = await self._ips_ref.document(ip).get()
        if not doc.exists:
            return None
        return self._to_entry(doc.to_dict())

    async def list_ips(self, status: IPStatus | None = None) -> list[IPEntry]:
        query = self._ips_ref
        if status:
            query = query.where("status", "==", status.value)
        entries = []
        async for doc in query.stream():
            entries.append(self._to_entry(doc.to_dict()))
        return sorted(entries, key=lambda e: e.created_at, reverse=True)

    async def update_ip_status(self, ip: str, status: IPStatus) -> bool:
        ref = self._ips_ref.document(ip)
        doc = await ref.get()
        if not doc.exists:
            return False
        await ref.update({"status": status.value})
        return True

    async def remove_ip(self, ip: str) -> bool:
        ref = self._ips_ref.document(ip)
        doc = await ref.get()
        if not doc.exists:
            return False
        await ref.delete()
        return True

    async def get_active_ips(self) -> list[IPEntry]:
        return await self.list_ips(status=IPStatus.ACTIVE)

    async def add_audit(self, entry: AuditEntry) -> None:
        data = entry.model_dump()
        data["timestamp"] = data["timestamp"].isoformat()
        doc_id = f"{entry.timestamp.strftime('%Y%m%d%H%M%S%f')}_{entry.ip}"
        await self._audits_ref.document(doc_id).set(data)

    async def list_audits(self, limit: int = 100) -> list[AuditEntry]:
        query = self._audits_ref.order_by(
            "timestamp", direction=firestore.Query.DESCENDING
        ).limit(limit)
        entries = []
        async for doc in query.stream():
            data = doc.to_dict()
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
            entries.append(AuditEntry(**data))
        return entries

    async def update_pipeline_status(self, ip: str, status: PipelineStatus) -> bool:
        ref = self._ips_ref.document(ip)
        doc = await ref.get()
        if not doc.exists:
            return False
        await ref.update({"pipeline_status": status.value})
        return True

    async def bulk_update_pipeline_status(
        self, from_status: PipelineStatus, to_status: PipelineStatus
    ) -> int:
        count = 0
        query = self._ips_ref.where("pipeline_status", "==", from_status.value)
        async for doc in query.stream():
            await doc.reference.update({"pipeline_status": to_status.value})
            count += 1
        return count

    async def try_lock(self, lock_id: str, ttl_seconds: int = 60) -> bool:
        ref = self._locks_ref.document(lock_id)
        now = datetime.now(timezone.utc)
        try:
            doc = await ref.get()
            if doc.exists:
                lock_data = doc.to_dict()
                expires = datetime.fromisoformat(lock_data.get("expires", ""))
                if expires > now:
                    return False
            await ref.set({
                "acquired_at": now.isoformat(),
                "expires": (now + timedelta(seconds=ttl_seconds)).isoformat(),
            })
            return True
        except Exception as e:
            logger.error(f"Lock error for {lock_id}: {e}")
            return False

    async def release_lock(self, lock_id: str) -> None:
        try:
            await self._locks_ref.document(lock_id).delete()
        except Exception as e:
            logger.error(f"Lock release error for {lock_id}: {e}")

    @staticmethod
    def _to_entry(data: dict) -> IPEntry:
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("expires_at"), str):
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
        if "pipeline_status" not in data:
            data["pipeline_status"] = "applied"
        return IPEntry(**data)
