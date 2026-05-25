from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Source(str, Enum):
    BURP = "burp"
    DASHBOARD = "dashboard"


class AnalysisMode(str, Enum):
    ANALYZE = "analyze"
    LEARN = "learn"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ContentEncoding(str, Enum):
    UTF_8 = "utf-8"
    BASE64 = "base64"
    OMITTED = "omitted"


class BodyOmittedReason(str, Enum):
    BINARY = "binary"
    TOO_LARGE = "too_large"
    STATIC_RESOURCE = "static_resource"


class AnalysisMetadata(BaseModel):
    content_encoding: ContentEncoding = ContentEncoding.UTF_8
    request_truncated: bool = False
    response_truncated: bool = False
    body_omitted_reason: BodyOmittedReason | None = None


class AnalyzeRequest(BaseModel):
    source: Source
    mode: AnalysisMode
    request_text: str = Field(min_length=1)
    response_text: str | None = None
    target_url: str | None = None
    metadata: AnalysisMetadata = Field(default_factory=AnalysisMetadata)


class Finding(BaseModel):
    title: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    attack_approach: str
    remediation: str
    owasp_category: str | None = None


class AnalysisResponse(BaseModel):
    analysis_id: str
    summary: str
    findings: list[Finding]
    redaction_applied: bool
    llm_status: Literal["ok", "repaired", "failed"]


class AnalysisHistoryItem(BaseModel):
    analysis_id: str
    created_at: str
    source: Source
    mode: AnalysisMode
    target_url: str | None = None
    request_text: str
    response_text: str | None = None
    metadata: AnalysisMetadata
    summary: str
    findings: list[Finding]
    redaction_applied: bool
    llm_status: Literal["ok", "repaired", "failed"]


class ProviderSettingsUpdate(BaseModel):
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    api_key: str | None = Field(default=None)


class ProviderSettingsResponse(BaseModel):
    provider: str
    model: str
    has_api_key: bool
    masked_api_key: str | None = None


class GuardedPayload(BaseModel):
    request_text: str
    response_text: str | None
    metadata: AnalysisMetadata

