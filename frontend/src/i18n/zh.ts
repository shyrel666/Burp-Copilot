export const zh = {
  // Sidebar
  brand_name: 'Burp AI',
  brand_sub: 'HTTP 分析器',
  nav_analyze: '分析',
  nav_batch: '批量',
  nav_history: '历史',
  nav_settings: '设置',

  // Topbar
  view_analyze: '手动分析',
  view_batch: '批量分析',
  view_history: '分析历史',
  view_settings: '提供商设置',
  subtitle: '本地优先的授权 HTTP 安全审查分析。',
  status_redaction: '需要脱敏',

  // Analyze
  mode_analyze: '分析',
  mode_learn: '学习',
  label_target_url: '目标 URL',
  placeholder_target_url: 'https://example.test/path',
  label_request: '请求',
  placeholder_request: 'GET / HTTP/1.1\r\nHost: example.test\r\n\r\n',
  label_response: '响应',
  placeholder_response: 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n',
  btn_analyze: '分析',
  btn_analyzing: '分析中...',
  empty_state: '提交请求以查看脱敏后的发现。',

  // Result
  result_streaming: '流式分析中',
  result_stream_failed: '流式传输失败',
  result_waiting: '等待最终结果',
  result_not_complete: '分析未完成',
  result_stream_error: '流式传输结束但未返回结果，分析无法完成。',
  result_llm_status: 'LLM 状态',
  result_redacted: '已脱敏',
  result_not_redacted: '未脱敏',
  result_failed_notice: '分析失败。提供商响应无法转换为结构化发现。',
  finding_approach: '攻击方式',
  finding_remediation: '修复建议',
  finding_owasp: 'OWASP',

  // Batch
  batch_mode_label: '批量模式',
  batch_textarea_label: '批量请求（多个请求用 --- 分隔）',
  batch_placeholder: 'GET /api/users HTTP/1.1\r\nHost: example.test\r\n\r\n\n---\nGET /api/orders HTTP/1.1\r\nHost: example.test\r\n\r\n',
  btn_submit_batch: '提交批量',
  btn_submitting: '提交中...',
  task_queue: '任务队列',
  btn_refresh: '刷新',
  no_tasks: '队列中没有任务。',

  // History
  filter_all_modes: '所有模式',
  filter_any_severity: '任意严重性',
  filter_critical: '严重+',
  filter_high: '高+',
  filter_medium: '中+',
  filter_low: '低+',
  placeholder_target_host: '目标主机',
  btn_filter: '筛选',
  btn_clear: '清除',
  no_history: '暂无分析历史。',

  // Settings
  label_provider: '提供商',
  label_model: '模型',
  label_base_url: '基础 URL',
  placeholder_base_url: 'http://127.0.0.1:11434/v1',
  label_api_key: 'API 密钥',
  placeholder_api_key_keep: '留空保持当前密钥',
  placeholder_api_key_paste: '粘贴提供商密钥',
  configured_key: '已配置密钥',
  not_configured: '未配置',
  ollama_note: 'Ollama 在本地运行，不需要 API 密钥。',
  btn_save_provider: '保存提供商',

  // Stream status
  stream_redacting: '脱敏中',
  stream_calling_provider: '调用提供商',
  stream_parsing: '解析中',
  stream_persisted: '已保存',
  stream_failed: '失败',

  // Errors
  error_unexpected: '意外错误',
  error_batch_failed: '批量提交失败',
  error_cancel_failed: '取消失败',

  // Language
  lang_switch: '中/EN',
  lang_switch_label: '切换语言',
} as const;

export type LocaleKeys = keyof typeof zh;
