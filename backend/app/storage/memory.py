import copy
from app.storage.base import BaseStorage
from app.models.schemas import IPEntry, AuditEntry, IPStatus


class MemoryStorage(BaseStorage):

    def __init__(self):
        self._ips: dict[str, IPEntry] = {}
        self._audits: list[AuditEntry] = []

    async def add_ip(self, entry: IPEntry) -> None:
        self._ips[entry.ip] = entry

    async def get_ip(self, ip: str) -> IPEntry | None:
        return copy.deepcopy(self._ips.get(ip))

    async def list_ips(self, status: IPStatus | None = None) -> list[IPEntry]:
        entries = list(self._ips.values())
        if status:
            entries = [e for e in entries if e.status == status]
        return sorted(entries, key=lambda e: e.created_at, reverse=True)

    async def update_ip_status(self, ip: str, status: IPStatus) -> bool:
        if ip not in self._ips:
            return False
        self._ips[ip] = self._ips[ip].model_copy(update={"status": status})
        return True

    async def remove_ip(self, ip: str) -> bool:
        if ip not in self._ips:
            return False
        del self._ips[ip]
        return True

    async def get_active_ips(self) -> list[IPEntry]:
        return [e for e in self._ips.values() if e.status == IPStatus.ACTIVE]

    async def add_audit(self, entry: AuditEntry) -> None:
        self._audits.append(entry)

    async def list_audits(self, limit: int = 100) -> list[AuditEntry]:
        return sorted(self._audits, key=lambda e: e.timestamp, reverse=True)[:limit]
