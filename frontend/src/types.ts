export type Mode = 'analyze' | 'learn';
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface Finding {
  title: string;
  severity: Severity;
  confidence: number;
  evidence: string;
  attack_approach: string;
  remediation: string;
  owasp_category: string | null;
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
  provider: string;
  model: string;
  has_api_key: boolean;
  masked_api_key: string | null;
}
