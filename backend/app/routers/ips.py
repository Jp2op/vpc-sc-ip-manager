from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    AddIPRequest, RemoveIPRequest, IPEntry, IPListResponse,
    AuditLogResponse, MessageResponse, IPStatus,
)
from app.services.ip_service import IPService
from app.services.scheduler import list_scheduled_jobs

router = APIRouter(tags=["IP Management"])

_service: IPService | None = None


def init_service(service: IPService):
    global _service
    _service = service


def _svc() -> IPService:
    if _service is None:
        raise RuntimeError("IPService not initialized")
    return _service


@router.post("/ips", response_model=IPEntry, status_code=201)
async def add_ip(request: AddIPRequest):
    """Whitelist an IP. Set duration_minutes=0 for permanent access."""
    try:
        return await _svc().add_ip(request)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/ips/{ip}", response_model=MessageResponse)
async def remove_ip(ip: str, body: RemoveIPRequest | None = None):
    """Remove an IP from the whitelist."""
    reason = body.reason if body else "Manual removal"
    try:
        await _svc().remove_ip(ip, reason)
        return MessageResponse(message=f"IP {ip} removed", ip=ip)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/ips", response_model=IPListResponse)
async def list_ips(status: IPStatus | None = Query(None)):
    """List IPs. Filter with ?status=active|expired|removed"""
    return await _svc().list_ips(status)


@router.get("/ips/{ip}", response_model=IPEntry)
async def get_ip(ip: str):
    """Get details of a specific IP."""
    entry = await _svc().get_ip(ip)
    if not entry:
        raise HTTPException(status_code=404, detail=f"IP {ip} not found")
    return entry


@router.get("/audit", response_model=AuditLogResponse)
async def get_audit_log(limit: int = Query(100, ge=1, le=1000)):
    """Audit log of all IP changes."""
    return await _svc().get_audit_log(limit)


@router.get("/debug/jobs")
async def debug_jobs():
    """List scheduled expiry jobs."""
    return {"jobs": list_scheduled_jobs()}
