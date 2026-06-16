import logging
from datetime import datetime, timedelta, timezone

from app.models.schemas import (
    IPEntry, IPStatus, AuditEntry, AuditAction,
    AddIPRequest, IPListResponse, AuditLogResponse,
)
from app.storage.base import BaseStorage
from app.services.github_service import GitHubService
from app.services.scheduler import schedule_ip_expiry, cancel_ip_expiry

logger = logging.getLogger(__name__)


class IPService:

    def __init__(self, storage: BaseStorage, github: GitHubService):
        self.storage = storage
        self.github = github

    async def add_ip(self, request: AddIPRequest) -> IPEntry:
        existing = await self.storage.get_ip(request.ip)
        if existing and existing.status == IPStatus.ACTIVE:
            raise ValueError(f"IP {request.ip} is already active")

        now = datetime.now(timezone.utc)
        expires_at = None
        if request.duration_minutes > 0:
            expires_at = now + timedelta(minutes=request.duration_minutes)

        entry = IPEntry(
            ip=request.ip,
            name=request.name,
            reason=request.reason,
            duration_minutes=request.duration_minutes,
            status=IPStatus.ACTIVE,
            created_at=now,
            expires_at=expires_at,
        )

        await self.storage.add_ip(entry)

        await self.storage.add_audit(AuditEntry(
            ip=request.ip,
            name=request.name,
            action=AuditAction.ADDED,
            reason=request.reason,
            timestamp=now,
            performed_by=request.name,
        ))

        if expires_at:
            schedule_ip_expiry(request.ip, expires_at, self._on_expire)

        active = await self.storage.get_active_ips()
        await self.github.commit_config(
            active, f"Add IP {request.ip} ({request.name}): {request.reason}"
        )

        logger.info(f"Added {request.ip} by {request.name}, expires: {expires_at or 'never'}")
        return entry

    async def remove_ip(self, ip: str, reason: str = "Manual removal") -> bool:
        existing = await self.storage.get_ip(ip)
        if not existing:
            raise ValueError(f"IP {ip} not found")
        if existing.status != IPStatus.ACTIVE:
            raise ValueError(f"IP {ip} is not active (status: {existing.status})")

        cancel_ip_expiry(ip)
        await self.storage.update_ip_status(ip, IPStatus.REMOVED)

        await self.storage.add_audit(AuditEntry(
            ip=ip,
            name=existing.name,
            action=AuditAction.REMOVED,
            reason=reason,
            timestamp=datetime.now(timezone.utc),
            performed_by="manual",
        ))

        active = await self.storage.get_active_ips()
        await self.github.commit_config(active, f"Remove IP {ip}: {reason}")

        logger.info(f"Removed {ip}: {reason}")
        return True

    async def expire_ip(self, ip: str) -> bool:
        existing = await self.storage.get_ip(ip)
        if not existing or existing.status != IPStatus.ACTIVE:
            logger.warning(f"Expiry fired for {ip} but not active, skipping")
            return False

        await self.storage.update_ip_status(ip, IPStatus.EXPIRED)

        await self.storage.add_audit(AuditEntry(
            ip=ip,
            name=existing.name,
            action=AuditAction.EXPIRED,
            reason=f"Duration of {existing.duration_minutes} min expired",
            timestamp=datetime.now(timezone.utc),
            performed_by="scheduler",
        ))

        active = await self.storage.get_active_ips()
        await self.github.commit_config(
            active, f"Auto-expire IP {ip} (duration: {existing.duration_minutes}min)"
        )

        logger.info(f"Expired {ip} ({existing.duration_minutes}min)")
        return True

    async def get_ip(self, ip: str) -> IPEntry | None:
        return await self.storage.get_ip(ip)

    async def list_ips(self, status: IPStatus | None = None) -> IPListResponse:
        entries = await self.storage.list_ips(status)
        active = len([e for e in entries if e.status == IPStatus.ACTIVE])
        return IPListResponse(total=len(entries), active_count=active, ips=entries)

    async def get_audit_log(self, limit: int = 100) -> AuditLogResponse:
        entries = await self.storage.list_audits(limit)
        return AuditLogResponse(total=len(entries), entries=entries)

    async def _on_expire(self, ip: str):
        logger.info(f"Expiry callback fired: {ip}")
        await self.expire_ip(ip)
