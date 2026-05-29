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
  no_findings: '该分析未报告任何发现。',

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

  // Dashboard
  nav_dashboard: '概览',
  view_dashboard: '安全态势概览',
  mode_recon: '侦察',
  compliance_banner: '仅用于已授权的安全测试。AI 给出的结论需人工验证，可能存在误报或漏报。',
  dashboard_total: '总分析数',
  dashboard_success_rate: '成功率',
  dashboard_top_vuln: '最常见漏洞类型',
  dashboard_severity_chart: '严重性分布',
  dashboard_recent: '最近发现',
  dashboard_attack_surface: '攻击面态势 · 建议优先测试',
  dashboard_empty_title: '还没有分析数据',
  dashboard_empty_hint: '在 Burp 中开启自动分析，或到「分析」页提交一条流量，概览将自动出现。',
  dashboard_no_recent: '暂无发现。',
  dashboard_none: '无',
  time_now: '刚刚',
  time_minute_suffix: '分钟前',
  time_hour_suffix: '小时前',
  time_day_suffix: '天前',

  // Attack surface
  surface_priority: '优先级',
  surface_findings: '发现',
  surface_auth: '需认证',
  surface_no_auth: '无认证',
  surface_params: '参数',
  surface_no_endpoints: '暂无端点数据。',

  // Architecture & roadmap
  arch_title: '架构指纹',
  arch_select_host: '选择目标',
  arch_system_types: '系统类型',
  arch_auth: '认证方式',
  arch_tech: '技术栈',
  arch_confidence: '置信度',
  arch_unknown: '未知',
  arch_generate_roadmap: '生成测试路线图',
  roadmap_title: '分阶段测试路线图',
  roadmap_generating: '正在生成路线图...',
  roadmap_objective: '目标',
  roadmap_target: '测试对象',
  roadmap_suspected: '怀疑漏洞',
  roadmap_reason: '理由',
  roadmap_priority: '优先级',
  roadmap_empty: '选择一个目标主机并生成路线图。',
  roadmap_failed: '路线图生成失败，请检查提供商配置后重试。',

  // Finding extras
  finding_verify: '人工验证步骤',
  finding_priority: '测试优先级',

  // History detail raw
  detail_show_raw: '查看脱敏后报文',
  detail_hide_raw: '隐藏报文',
  detail_raw_request: '请求（已脱敏）',
  detail_raw_response: '响应（已脱敏）',

  // Test provider
  btn_test_provider: '测试连接',
  test_provider_ok: '连接正常',
  test_provider_fail: '连接失败',
  test_provider_testing: '测试中...',

  // Language
  lang_switch: '中/EN',
  lang_switch_label: '切换语言',
} as const;

export type LocaleKeys = keyof typeof zh;
