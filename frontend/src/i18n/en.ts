import type { LocaleKeys } from './zh';

export const en: Record<LocaleKeys, string> = {
  // Sidebar
  brand_name: 'Burp Copilot',
  brand_sub: 'AI Security Copilot',
  nav_analyze: 'Analyze',
  nav_batch: 'Batch',
  nav_history: 'History',
  nav_settings: 'Settings',

  // Topbar
  view_analyze: 'Manual analysis',
  view_batch: 'Batch analysis',
  view_history: 'Analysis history',
  view_settings: 'Provider settings',
  subtitle: 'Local-first analysis for authorized HTTP security review.',
  status_redaction: 'Redaction required',

  // Analyze
  mode_analyze: 'Analyze',
  mode_learn: 'Learn',
  label_target_url: 'Target URL',
  placeholder_target_url: 'https://example.test/path',
  label_request: 'Request',
  placeholder_request: 'GET / HTTP/1.1\r\nHost: example.test\r\n\r\n',
  label_response: 'Response',
  placeholder_response: 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n',
  btn_analyze: 'Analyze',
  btn_analyzing: 'Analyzing...',
  empty_state: 'Submit a request to view redacted findings.',

  // Result
  result_streaming: 'Streaming analysis',
  result_stream_failed: 'Streaming failed',
  result_waiting: 'Waiting for final result',
  result_not_complete: 'Analysis did not complete',
  result_stream_error: 'Stream ended without a result. The analysis could not be completed.',
  result_llm_status: 'LLM status',
  result_redacted: 'Redacted',
  result_not_redacted: 'Not redacted',
  result_failed_notice: 'Analysis failed. The provider response could not be converted into structured findings.',
  finding_approach: 'Approach',
  finding_remediation: 'Remediation',
  finding_owasp: 'OWASP',

  // Batch
  batch_mode_label: 'Batch mode',
  batch_textarea_label: 'Batch requests (separate multiple with ---)',
  batch_placeholder: 'GET /api/users HTTP/1.1\r\nHost: example.test\r\n\r\n\n---\nGET /api/orders HTTP/1.1\r\nHost: example.test\r\n\r\n',
  btn_submit_batch: 'Submit batch',
  btn_submitting: 'Submitting...',
  task_queue: 'Task queue',
  btn_refresh: 'Refresh',
  no_tasks: 'No tasks in queue.',

  // History
  filter_all_modes: 'All modes',
  filter_any_severity: 'Any severity',
  filter_critical: 'Critical+',
  filter_high: 'High+',
  filter_medium: 'Medium+',
  filter_low: 'Low+',
  placeholder_target_host: 'Target host',
  btn_filter: 'Filter',
  btn_clear: 'Clear',
  no_history: 'No analysis history yet.',
  no_findings: 'No findings reported for this analysis.',

  // Settings
  label_provider: 'Provider',
  label_model: 'Model',
  label_base_url: 'Base URL',
  placeholder_base_url: 'http://127.0.0.1:11434/v1',
  label_api_key: 'API key',
  placeholder_api_key_keep: 'Leave blank to keep current key',
  placeholder_api_key_paste: 'Paste provider key',
  configured_key: 'Configured key',
  not_configured: 'Not configured',
  ollama_note: 'Ollama runs locally and does not require an API key.',
  btn_save_provider: 'Save Provider',

  // Stream status
  stream_redacting: 'Redacting',
  stream_calling_provider: 'Calling provider',
  stream_parsing: 'Parsing',
  stream_persisted: 'Persisted',
  stream_failed: 'Failed',

  // Errors
  error_unexpected: 'Unexpected error',
  error_batch_failed: 'Batch submit failed',
  error_cancel_failed: 'Cancel failed',

  // Dashboard
  nav_dashboard: 'Overview',
  view_dashboard: 'Security posture overview',
  mode_recon: 'Recon',
  compliance_banner: 'For authorized security testing only. AI conclusions require manual verification and may contain false positives or negatives.',
  dashboard_total: 'Total analyses',
  dashboard_success_rate: 'Success rate',
  dashboard_top_vuln: 'Top vulnerability type',
  dashboard_severity_chart: 'Severity distribution',
  dashboard_recent: 'Recent findings',
  dashboard_attack_surface: 'Attack surface · suggested test order',
  dashboard_empty_title: 'No analysis data yet',
  dashboard_empty_hint: 'Enable auto-analysis in Burp, or submit one request on the Analyze page, and the overview will appear.',
  dashboard_no_recent: 'No findings yet.',
  dashboard_none: 'None',
  time_now: 'now',
  time_minute_suffix: 'm ago',
  time_hour_suffix: 'h ago',
  time_day_suffix: 'd ago',

  // Attack surface
  surface_priority: 'Priority',
  surface_findings: 'findings',
  surface_auth: 'auth',
  surface_no_auth: 'no auth',
  surface_params: 'params',
  surface_no_endpoints: 'No endpoint data yet.',

  // Architecture & roadmap
  arch_title: 'Architecture fingerprint',
  arch_select_host: 'Select target',
  arch_system_types: 'System type',
  arch_auth: 'Auth method',
  arch_tech: 'Tech stack',
  arch_confidence: 'Confidence',
  arch_unknown: 'Unknown',
  arch_generate_roadmap: 'Generate testing roadmap',
  roadmap_view: 'View testing roadmap',
  roadmap_regenerate: 'Regenerate roadmap',
  roadmap_title: 'Staged testing roadmap',
  roadmap_generating: 'Generating roadmap...',
  roadmap_objective: 'Objective',
  roadmap_target: 'Target',
  roadmap_suspected: 'Suspected vuln',
  roadmap_reason: 'Reason',
  roadmap_priority: 'Priority',
  roadmap_empty: 'Select a target host and generate a roadmap.',
  roadmap_failed: 'Roadmap generation failed. Check provider settings and retry.',

  // Finding extras
  finding_verify: 'Manual verification steps',
  finding_priority: 'Test priority',

  // History detail raw
  detail_show_raw: 'Show redacted traffic',
  detail_hide_raw: 'Hide traffic',
  detail_raw_request: 'Request (redacted)',
  detail_raw_response: 'Response (redacted)',

  // Test provider
  btn_test_provider: 'Test connection',
  test_provider_ok: 'Connection OK',
  test_provider_fail: 'Connection failed',
  test_provider_testing: 'Testing...',

  // Language
  lang_switch: '中/EN',
  lang_switch_label: 'Switch language',
};
