from abc import ABC, abstractmethod
from app.models.schemas import IPEntry, AuditEntry, IPStatus, PipelineStatus


class BaseStorage(ABC):

    @abstractmethod
    async def add_ip(self, entry: IPEntry) -> None: ...

    @abstractmethod
    async def get_ip(self, ip: str) -> IPEntry | None: ...

    @abstractmethod
    async def list_ips(self, status: IPStatus | None = None) -> list[IPEntry]: ...

    @abstractmethod
    async def update_ip_status(self, ip: str, status: IPStatus) -> bool: ...

    @abstractmethod
    async def remove_ip(self, ip: str) -> bool: ...

    @abstractmethod
    async def get_active_ips(self) -> list[IPEntry]: ...

    @abstractmethod
    async def add_audit(self, entry: AuditEntry) -> None: ...

    @abstractmethod
    async def list_audits(self, limit: int = 100) -> list[AuditEntry]: ...

    async def update_pipeline_status(self, ip: str, status: PipelineStatus) -> bool:
        """Update the pipeline status of a single IP."""
        return False

    async def bulk_update_pipeline_status(
        self, from_status: PipelineStatus, to_status: PipelineStatus
    ) -> int:
        """Update all IPs with from_status to to_status. Returns count updated."""
        return 0

    async def try_lock(self, lock_id: str, ttl_seconds: int = 60) -> bool:
        return True

    async def release_lock(self, lock_id: str) -> None:
        pass
