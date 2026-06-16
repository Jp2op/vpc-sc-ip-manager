from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum
import ipaddress


class IPStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REMOVED = "removed"


class AuditAction(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    EXPIRED = "expired"


# ---- Requests ----

class AddIPRequest(BaseModel):
    ip: str = Field(..., description="IPv4 address to whitelist")
    name: str = Field(..., min_length=1, max_length=100, description="Who is requesting")
    reason: str = Field(..., min_length=1, max_length=500, description="Why this IP needs access")
    duration_minutes: int = Field(
        ...,
        ge=0,
        description="Duration in minutes. 0 = permanent (no expiry)"
    )

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        try:
            addr = ipaddress.IPv4Address(v)
            return str(addr)
        except ipaddress.AddressValueError:
            raise ValueError(f"Invalid IPv4 address: {v}")


class RemoveIPRequest(BaseModel):
    reason: str = Field(default="Manual removal", max_length=500)


# ---- Responses ----

class IPEntry(BaseModel):
    ip: str
    name: str
    reason: str
    duration_minutes: int
    status: IPStatus
    created_at: datetime
    expires_at: datetime | None = None


class IPListResponse(BaseModel):
    total: int
    active_count: int
    ips: list[IPEntry]


class AuditEntry(BaseModel):
    ip: str
    name: str
    action: AuditAction
    reason: str
    timestamp: datetime
    performed_by: str = "system"


class AuditLogResponse(BaseModel):
    total: int
    entries: list[AuditEntry]


class MessageResponse(BaseModel):
    message: str
    ip: str | None = None
    expires_at: datetime | None = None


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
