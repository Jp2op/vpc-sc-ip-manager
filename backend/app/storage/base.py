from abc import ABC, abstractmethod
from app.models.schemas import IPEntry, AuditEntry, IPStatus


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

    async def try_lock(self, lock_id: str, ttl_seconds: int = 60) -> bool:
        """Try to acquire a distributed lock. Returns True if acquired."""
        return True  # Default: no-op (always succeeds for in-memory)

    async def release_lock(self, lock_id: str) -> None:
        """Release a distributed lock."""
        pass  # Default: no-op
