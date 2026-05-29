# Requirements Document

## Introduction

本文档定义了 Burp AI HTTP Traffic Analyzer 项目的两个核心增强功能：**Dashboard 概览页面**和**自动分析规则引擎**。Dashboard 概览页面为 Web 前端提供安全态势总览，用户打开仪表盘即可看到分析统计、严重性分布和最近发现。自动分析规则引擎使 Burp 扩展能够根据用户配置的作用域规则自动提交匹配的 HTTP 流量进行分析，无需手动干预。

## Glossary

- **Dashboard**: Web 前端的概览首页，展示分析统计和安全态势摘要
- **Statistics_API**: 后端提供聚合统计数据的 API 端点
- **Severity_Distribution**: 按严重性级别（critical、high、medium、low、info）分组的发现数量统计
- **Findings_Timeline**: 按时间排列的最近安全发现列表
- **Auto_Analysis_Engine**: Burp 扩展中负责监听 HTTP 流量并自动提交匹配请求进行分析的组件
- **Scope_Rule**: 用户配置的 URL 匹配模式，用于决定哪些 HTTP 流量应被自动分析
- **Proxy_Listener**: Burp 扩展中注册的 HTTP 流量监听器，拦截经过代理的请求/响应对
- **Highlight_Marker**: Burp Proxy History 中对已分析请求的视觉标记（颜色高亮和注释）
- **Backend**: FastAPI 后端服务，负责 LLM 调用、结果解析和数据持久化
- **Batch_API**: 后端已有的批量提交分析任务的 API（`/api/v1/batch/submit`）

## Requirements

### Requirement 1: Dashboard 统计 API

**User Story:** As a security analyst, I want to retrieve aggregated analysis statistics from the backend, so that the frontend can display an overview of the security posture.

#### Acceptance Criteria

1. WHEN a GET request is sent to `/api/v1/statistics`, THE Statistics_API SHALL return a JSON object containing total analysis count, severity distribution counts, success rate, and top vulnerability types
2. THE Statistics_API SHALL compute severity distribution as a mapping of each Severity level to its corresponding finding count
3. THE Statistics_API SHALL compute success rate as the ratio of analyses with `llm_status` equal to "ok" or "repaired" to total analyses, returning 0% as a normal statistical value when no analyses have succeeded
4. THE Statistics_API SHALL compute top vulnerability types as the five most frequent `owasp_category` values across all findings
5. WHEN the optional query parameter `since` is provided, THE Statistics_API SHALL restrict all computations to analyses created on or after the specified ISO 8601 timestamp
6. WHEN no analysis records exist, THE Statistics_API SHALL return zero counts and empty lists without error

### Requirement 2: 最近发现时间线 API

**User Story:** As a security analyst, I want to see recent findings in chronological order, so that I can quickly identify newly discovered vulnerabilities.

#### Acceptance Criteria

1. WHEN a GET request is sent to `/api/v1/statistics/recent-findings`, THE Statistics_API SHALL return the 20 most recent findings ordered by analysis creation time descending
2. THE Statistics_API SHALL include for each finding: the finding title, severity, confidence, owasp_category, the parent analysis_id, target_url, and created_at timestamp
3. WHEN the optional query parameter `limit` is provided with a value between 1 and 100, THE Statistics_API SHALL return at most that many findings

### Requirement 3: Dashboard 概览页面

**User Story:** As a security analyst, I want to see a visual overview when I open the web dashboard, so that I can immediately understand the current security posture without manual navigation.

#### Acceptance Criteria

1. WHEN the user navigates to the Dashboard view, THE Dashboard SHALL display the total analysis count, success rate percentage, and top vulnerability type as quick-stat cards
2. THE Dashboard SHALL display a donut chart showing the severity distribution of all findings
3. THE Dashboard SHALL display a timeline list of recent findings with severity badge, title, target URL, and relative timestamp
4. WHEN the Statistics_API returns zero analyses, THE Dashboard SHALL display only an empty state message guiding the user to perform their first analysis, hiding all other dashboard elements including stat cards, donut chart, and timeline
5. THE Dashboard SHALL be the default view when the application loads (replacing the current Analyze view as the landing page)
6. THE Dashboard SHALL support the existing i18n system with both Chinese and English translations

### Requirement 4: Scope 规则配置持久化

**User Story:** As a penetration tester, I want to configure URL scope rules in the Burp extension, so that I can define which targets should be automatically analyzed.

#### Acceptance Criteria

1. THE Auto_Analysis_Engine SHALL persist scope rules using the Montoya persistence API so that rules survive Burp restarts
2. WHEN the user adds a Scope_Rule with a glob pattern (e.g., `*.target.com`), THE Auto_Analysis_Engine SHALL store the pattern in the persisted rule list
3. WHEN the user removes a Scope_Rule, THE Auto_Analysis_Engine SHALL delete the pattern from the persisted rule list
4. THE Auto_Analysis_Engine SHALL support at least 50 concurrent Scope_Rule entries
5. WHEN a Scope_Rule pattern is empty or contains only whitespace, THE Auto_Analysis_Engine SHALL reject the rule and display a validation error; pre-existing stored empty patterns SHALL be preserved and only future additions SHALL be validated
6. WHEN removing a Scope_Rule, THE Auto_Analysis_Engine SHALL allow removal regardless of whether the pattern is valid or invalid

### Requirement 5: Scope 规则匹配

**User Story:** As a penetration tester, I want scope rules to match HTTP traffic by URL pattern, so that only relevant targets are automatically analyzed.

#### Acceptance Criteria

1. WHEN an HTTP request URL matches any configured Scope_Rule glob pattern, THE Auto_Analysis_Engine SHALL classify the request as in-scope
2. THE Auto_Analysis_Engine SHALL support glob wildcards where `*` matches any sequence of characters within a single domain segment and `**` matches across segments
3. WHEN a Scope_Rule pattern does not contain a scheme prefix, THE Auto_Analysis_Engine SHALL match against both HTTP and HTTPS URLs
4. THE Auto_Analysis_Engine SHALL perform case-insensitive matching on the host portion of the URL
5. WHEN no Scope_Rule is configured, THE Auto_Analysis_Engine SHALL not classify any request as in-scope (auto-analysis is disabled)

### Requirement 6: 自动流量提交

**User Story:** As a penetration tester, I want in-scope HTTP traffic to be automatically submitted for analysis, so that I don't need to manually select each request.

#### Acceptance Criteria

1. WHEN an HTTP response is received for an in-scope request, THE Proxy_Listener SHALL submit the request-response pair to the Backend via the Batch_API
2. THE Proxy_Listener SHALL use the existing HttpMessageFilter to prepare the request-response pair before submission (applying truncation, binary detection, and static resource filtering)
3. WHEN the HttpMessageFilter classifies a request as a static resource, THE Proxy_Listener SHALL skip submission for that request
4. THE Proxy_Listener SHALL submit requests asynchronously without blocking Burp's proxy processing
5. THE Proxy_Listener SHALL enforce a rate limit of at most 10 submissions per second to avoid overwhelming the Backend
6. IF the Backend returns an error response, THEN THE Proxy_Listener SHALL log the error to Burp's output log and continue processing subsequent requests

### Requirement 7: Proxy History 高亮标记

**User Story:** As a penetration tester, I want analyzed requests to be visually highlighted in Burp's Proxy History, so that I can quickly identify which requests have been processed and their results.

#### Acceptance Criteria

1. WHEN a batch task completes successfully for an auto-submitted request, THE Auto_Analysis_Engine SHALL apply a color highlight to the corresponding Proxy History entry
2. THE Auto_Analysis_Engine SHALL use distinct highlight colors based on the highest severity finding: red for critical, orange for high, yellow for medium, blue for low, and gray for info-only
3. WHEN a batch task completes successfully, THE Auto_Analysis_Engine SHALL add a comment annotation to the Proxy History entry containing the analysis summary text; IF the comment addition fails, THEN THE Auto_Analysis_Engine SHALL continue without the comment
4. WHEN a batch task fails and no severity findings were produced, THE Auto_Analysis_Engine SHALL apply a distinct highlight color (magenta) to indicate analysis failure
5. WHEN a batch task fails but severity findings were produced before the failure, THE Auto_Analysis_Engine SHALL use severity-based highlight colors instead of the failure color
5. THE Auto_Analysis_Engine SHALL poll the Backend for task completion status at an interval of 5 seconds for pending auto-submitted tasks

### Requirement 8: 自动分析 UI 配置面板

**User Story:** As a penetration tester, I want a configuration panel in the Burp extension to manage auto-analysis settings, so that I can enable/disable auto-analysis and manage scope rules through a GUI.

#### Acceptance Criteria

1. THE Auto_Analysis_Engine SHALL provide a settings section in the existing Burp extension panel with a toggle to enable or disable auto-analysis
2. WHEN auto-analysis is disabled via the toggle, THE Proxy_Listener SHALL stop submitting in-scope requests
3. THE Auto_Analysis_Engine SHALL display a list of configured Scope_Rule entries with add and remove controls
4. THE Auto_Analysis_Engine SHALL display a counter showing the number of requests auto-submitted in the current session
5. WHEN the user clicks the add button with a valid pattern in the input field, THE Auto_Analysis_Engine SHALL persist the pattern immediately; patterns MAY be persisted independently of their visibility in the Scope_Rule list
