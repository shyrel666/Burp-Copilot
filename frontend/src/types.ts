export type Mode = 'analyze' | 'learn' | 'recon';
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type ProviderName = 'openai' | 'openai-compatible' | 'deepseek' | 'ollama';
export type StreamStatus = 'redacting' | 'calling_provider' | 'parsing' | 'persisted' | 'failed';

export interface Finding {
  title: string;
  severity: Severity;
  confidence: number;
  evidence: string;
  attack_approach: string;
  remediation: string;
  owasp_category: string | null;
  verification_steps?: string[];
  priority?: number | null;
}

export interface AnalysisResponse {
  analysis_id: string;
  summary: string;
  findings: Finding[];
  redaction_applied: boolean;
  llm_status: 'ok' | 'repaired' | 'failed';
}

export interface AnalysisHistoryItem extends AnalysisResponse {
  created_at: string;
  source: 'burp' | 'dashboard';
  mode: Mode;
  target_url: string | null;
  request_text: string;
  response_text: string | null;
}

export interface ProviderSettings {
  provider: ProviderName;
  model: string;
  has_api_key: boolean;
  masked_api_key: string | null;
  base_url: string | null;
}

export type TaskStatus = 'queued' | 'running' | 'done' | 'failed' | 'cancelled';

export interface TaskInfo {
  task_id: string;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
  source: 'burp' | 'dashboard';
  mode: Mode;
  target_url: string | null;
  analysis_id: string | null;
  error_message: string | null;
}

export interface HistoryFilters {
  mode?: Mode;
  min_severity?: Severity;
  target_host?: string;
  since?: string;
  until?: string;
  limit?: number;
  offset?: number;
}

export interface SeverityDistribution {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

export interface TopVulnerabilityType {
  owasp_category: string;
  count: number;
}

export interface StatisticsResponse {
  total_analyses: number;
  success_rate: number;
  severity_distribution: SeverityDistribution;
  top_vulnerability_types: TopVulnerabilityType[];
}

export interface RecentFinding {
  title: string;
  severity: Severity;
  confidence: number;
  owasp_category: string | null;
  analysis_id: string;
  target_url: string | null;
  created_at: string;
}

export interface AttackSurfaceEndpoint {
  host: string | null;
  method: string;
  path_template: string;
  hit_count: number;
  param_names: string[];
  has_auth_boundary: boolean;
  finding_count: number;
  max_severity: Severity | null;
  priority_score: number;
}

export interface AttackSurfaceResponse {
  total_endpoints: number;
  endpoints: AttackSurfaceEndpoint[];
}

export interface ArchitectureProfile {
  host: string | null;
  system_types: string[];
  auth_methods: string[];
  tech_stack: string[];
  evidence: string[];
  endpoint_count: number;
  confidence: number;
}

export interface RoadmapStep {
  target: string;
  suspected_vuln: string;
  reason: string;
  verification_steps: string[];
  priority: number | null;
}

export interface RoadmapStage {
  stage: string;
  objective: string;
  steps: RoadmapStep[];
}

export interface RoadmapResponse {
  host: string | null;
  architecture: ArchitectureProfile;
  stages: RoadmapStage[];
  llm_status: 'ok' | 'repaired' | 'failed';
  notes: string | null;
}
