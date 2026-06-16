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
        # Give GitHub service access to storage for debounced commits
        self.github.set_storage(storage)

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

        # Debounced — won't commit immediately, waits 30s for more changes
        await self.github.request_commit(
            f"Add IP {request.ip} ({request.name}): {request.reason}"
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

        await self.github.request_commit(f"Remove IP {ip}: {reason}")

        logger.info(f"Removed {ip}: {reason}")
        return True

    async def expire_ip(self, ip: str) -> bool:
        """Expire an IP. Uses Firestore lock if available to prevent concurrent expiry."""
        existing = await self.storage.get_ip(ip)
        if not existing or existing.status != IPStatus.ACTIVE:
            logger.warning(f"Expiry fired for {ip} but not active, skipping")
            return False

        # Try to acquire lock (prevents duplicate expiry from concurrent pods)
        lock_acquired = await self.storage.try_lock(f"expire_{ip}", ttl_seconds=60)
        if not lock_acquired:
            logger.info(f"Lock not acquired for {ip}, another instance is handling it")
            return False

        try:
            # Re-check status after acquiring lock
            existing = await self.storage.get_ip(ip)
            if not existing or existing.status != IPStatus.ACTIVE:
                logger.warning(f"Expiry for {ip}: status changed while acquiring lock, skipping")
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

            await self.github.request_commit(
                f"Auto-expire IP {ip} (duration: {existing.duration_minutes}min)"
            )

            logger.info(f"Expired {ip} ({existing.duration_minutes}min)")
            return True

        finally:
            await self.storage.release_lock(f"expire_{ip}")

    async def recover_on_startup(self):
        """Called on app startup. Recovers missed expiries and reschedules future ones.
        
        This makes the system crash-proof — if the pod restarts, all pending
        expiries are reloaded from storage.
        """
        active_ips = await self.storage.get_active_ips()
        now = datetime.now(timezone.utc)
        expired_count = 0
        rescheduled_count = 0

        for entry in active_ips:
            if entry.expires_at is None:
                continue  # Permanent IP, nothing to schedule

            if entry.expires_at <= now:
                # Missed expiry — expire immediately
                logger.info(f"Startup recovery: expiring missed IP {entry.ip} (was due {entry.expires_at})")
                await self.expire_ip(entry.ip)
                expired_count += 1
            else:
                # Future expiry — reschedule
                schedule_ip_expiry(entry.ip, entry.expires_at, self._on_expire)
                rescheduled_count += 1

        if expired_count or rescheduled_count:
            logger.info(f"Startup recovery: expired {expired_count}, rescheduled {rescheduled_count}")

            if expired_count > 0:
                # Force commit immediately for any expired IPs
                active_ips = await self.storage.get_active_ips()
                await self.github.force_commit(
                    active_ips,
                    f"Startup recovery: expired {expired_count} missed IP(s)"
                )
        else:
            logger.info("Startup recovery: nothing to recover")

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
