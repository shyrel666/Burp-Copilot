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
    RECON = "recon"


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


class ProviderName(str, Enum):
    OPENAI = "openai"
    OPENAI_COMPATIBLE = "openai-compatible"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"


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
    verification_steps: list[str] = Field(default_factory=list)
    priority: int | None = Field(default=None, ge=1, le=5)


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


class SeverityDistribution(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class TopVulnerabilityType(BaseModel):
    owasp_category: str
    count: int


class StatisticsResponse(BaseModel):
    total_analyses: int
    success_rate: float = Field(ge=0.0, le=1.0)
    severity_distribution: SeverityDistribution
    top_vulnerability_types: list[TopVulnerabilityType]


class RecentFinding(BaseModel):
    title: str
    severity: Severity
    confidence: float
    owasp_category: str | None = None
    analysis_id: str
    target_url: str | None = None
    created_at: str


class AttackSurfaceEndpoint(BaseModel):
    host: str | None = None
    method: str
    path_template: str
    hit_count: int
    param_names: list[str] = Field(default_factory=list)
    has_auth_boundary: bool = False
    finding_count: int = 0
    max_severity: Severity | None = None
    priority_score: float = 0.0


class AttackSurfaceResponse(BaseModel):
    total_endpoints: int
    endpoints: list[AttackSurfaceEndpoint]


class ArchitectureProfile(BaseModel):
    host: str | None = None
    system_types: list[str] = Field(default_factory=list)
    auth_methods: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    endpoint_count: int = 0
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class RoadmapRequest(BaseModel):
    host: str = Field(min_length=1)


class RoadmapStep(BaseModel):
    target: str
    suspected_vuln: str
    reason: str
    verification_steps: list[str] = Field(default_factory=list)
    priority: int | None = Field(default=None, ge=1, le=5)


class RoadmapStage(BaseModel):
    stage: str
    objective: str = ""
    steps: list[RoadmapStep] = Field(default_factory=list)


class RoadmapResponse(BaseModel):
    host: str | None = None
    architecture: ArchitectureProfile
    stages: list[RoadmapStage] = Field(default_factory=list)
    llm_status: Literal["ok", "repaired", "failed"] = "ok"
    notes: str | None = None


class ProviderSettingsUpdate(BaseModel):
    provider: ProviderName
    model: str = Field(min_length=1)
    api_key: str | None = Field(default=None)
    base_url: str | None = Field(default=None)


class ProviderSettingsResponse(BaseModel):
    provider: ProviderName
    model: str
    has_api_key: bool
    masked_api_key: str | None = None
    base_url: str | None = None


class GuardedPayload(BaseModel):
    request_text: str
    response_text: str | None
    metadata: AnalysisMetadata


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchItem(BaseModel):
    source: Source = Source.DASHBOARD
    mode: AnalysisMode
    request_text: str = Field(min_length=1)
    response_text: str | None = None
    target_url: str | None = None
    metadata: AnalysisMetadata = Field(default_factory=AnalysisMetadata)


class BatchSubmitRequest(BaseModel):
    items: list[BatchItem] = Field(min_length=1, max_length=20)


class TaskInfo(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: str
    updated_at: str
    source: Source
    mode: AnalysisMode
    target_url: str | None = None
    analysis_id: str | None = None
    error_message: str | None = None


class BatchSubmitResponse(BaseModel):
    tasks: list[TaskInfo]
