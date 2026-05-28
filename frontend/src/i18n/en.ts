import type { LocaleKeys } from './zh';

export const en: Record<LocaleKeys, string> = {
  // Sidebar
  brand_name: 'Burp AI',
  brand_sub: 'HTTP Analyzer',
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

  // Language
  lang_switch: '中/EN',
  lang_switch_label: 'Switch language',
};
