# Implementation Plan: Dashboard Overview & Auto-Analysis

## Implementation status (landed)

The "AI pentest copilot" work landed with an extended scope beyond this original spec. Implemented:

- Backend: Statistics API + recent-findings + attack-surface aggregation (`statistics_service.py`), architecture fingerprinting (`fingerprint_service.py`), endpoint inventory (`endpoint_inventory.py` + `endpoints` table), staged roadmap synthesis (`roadmap_service.py`), recon analysis mode and `verification_steps`/`priority` finding fields. Covered by pytest + hypothesis property tests (Properties 1-5).
- Frontend: Dashboard as default landing view (`Dashboard.tsx`) with stat cards, SVG severity donut, attack surface panel, architecture card, staged roadmap, recent-findings timeline; test-connection button; redacted raw traffic in history detail. Covered by vitest.
- Burp: scope rule store/matcher, token-bucket rate limiter, proxy auto-analysis listener, Site Map scan, task poller, severity-based Proxy History highlighting, and the auto-analysis config panel. Pure logic covered by JUnit (jqwik not added; equivalent example/parameterized tests used).
- Active verification remains intentionally unimplemented (reserved seam at `POST /api/v1/recon/verify`).

## Overview

本实现计划将 Dashboard 概览页面和自动分析规则引擎分解为可增量执行的编码任务。后端使用 Python (FastAPI)，前端使用 TypeScript (React + Vite)，Burp 扩展使用 Java。每个任务构建在前一个任务之上，确保无孤立代码。

## Tasks

- [ ] 1. Backend: Statistics API 实现
  - [ ] 1.1 新增 Statistics 响应模型和服务层
    - 在 `backend/app/models/schemas.py` 中新增 `SeverityDistribution`、`TopVulnerabilityType`、`StatisticsResponse`、`RecentFinding` 模型
    - 新建 `backend/app/services/statistics_service.py`，实现 `StatisticsService` 类
    - 实现 `get_statistics(since)` 方法：聚合 total_analyses、severity_distribution、success_rate、top_vulnerability_types
    - 实现 `get_recent_findings(limit)` 方法：查询最近发现并按 created_at 降序排列
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3_

  - [ ] 1.2 注册 Statistics API 路由
    - 在 `backend/app/main.py` 中新增 `GET /api/v1/statistics` 端点，接受可选 `since` 查询参数
    - 新增 `GET /api/v1/statistics/recent-findings` 端点，接受可选 `limit` 查询参数 (1-100, 默认 20)
    - 对无效 `since` 格式返回 HTTP 422
    - 无数据时返回零值和空列表 (HTTP 200)
    - _Requirements: 1.1, 1.5, 1.6, 2.1, 2.3_

  - [ ]* 1.3 编写 Statistics API 单元测试
    - 新建 `backend/tests/test_statistics_service.py`
    - 测试空数据库场景返回零值
    - 测试单条/多条记录的聚合正确性
    - 测试 `since` 过滤逻辑
    - 测试 `limit` 参数边界 (1, 20, 100)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.3_

  - [ ]* 1.4 编写 Statistics 属性测试 — Property 1: Severity distribution sum
    - **Property 1: Severity distribution sum equals total findings**
    - 使用 hypothesis 库，最少 100 次迭代
    - 验证 severity_distribution 各值之和等于所有 findings 总数
    - **Validates: Requirements 1.2**

  - [ ]* 1.5 编写 Statistics 属性测试 — Property 2: Success rate formula
    - **Property 2: Success rate formula correctness**
    - 使用 hypothesis 库，最少 100 次迭代
    - 验证 success_rate = count(llm_status in ok/repaired) / total，无成功记录时为 0.0
    - **Validates: Requirements 1.3**

  - [ ]* 1.6 编写 Statistics 属性测试 — Property 3: Top vulnerability types ranking
    - **Property 3: Top vulnerability types ranking**
    - 使用 hypothesis 库，最少 100 次迭代
    - 验证返回的 top 5 类别按 count 降序，且无遗漏更高频类别
    - **Validates: Requirements 1.4**

  - [ ]* 1.7 编写 Statistics 属性测试 — Property 4: Since filter
    - **Property 4: Since filter restricts computation scope**
    - 使用 hypothesis 库，最少 100 次迭代
    - 验证所有统计计算仅包含 created_at >= since 的记录
    - **Validates: Requirements 1.5**

  - [ ]* 1.8 编写 Statistics 属性测试 — Property 5: Recent findings ordering
    - **Property 5: Recent findings ordering and field completeness**
    - 使用 hypothesis 库，最少 100 次迭代
    - 验证返回结果按 created_at 降序，数量不超过 limit，且每项包含所有必需字段
    - **Validates: Requirements 2.1, 2.2, 2.3**

- [ ] 2. Checkpoint - 后端 Statistics API 验证
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Frontend: Dashboard 概览页面
  - [ ] 3.1 新增 Dashboard API 客户端函数和类型定义
    - 在 `frontend/src/types.ts` 中新增 `SeverityDistribution`、`TopVulnerabilityType`、`StatisticsResponse`、`RecentFinding` 接口
    - 在 `frontend/src/api/client.ts` 中新增 `fetchStatistics(since?)` 和 `fetchRecentFindings(limit?)` 函数
    - _Requirements: 1.1, 2.1_

  - [ ] 3.2 新增 Dashboard i18n 翻译键
    - 在 `frontend/src/i18n/zh.ts` 和 `frontend/src/i18n/en.ts` 中新增 Dashboard 相关翻译键
    - 包含：nav_dashboard、dashboard_total、dashboard_success_rate、dashboard_top_vuln、dashboard_severity_chart、dashboard_recent、dashboard_empty_state 等
    - _Requirements: 3.6_

  - [ ] 3.3 实现 Dashboard 视图组件
    - 新建 Dashboard 组件文件（StatCards、SeverityDonut、FindingsTimeline、EmptyDashboard）
    - StatCards 展示总分析数、成功率百分比、Top 漏洞类型
    - SeverityDonut 使用纯 CSS/SVG 实现 donut chart
    - FindingsTimeline 展示最近发现列表（severity badge、title、target URL、相对时间）
    - EmptyDashboard 在无数据时显示引导信息，隐藏所有其他元素
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ] 3.4 集成 Dashboard 为默认视图
    - 修改 `frontend/src/App.tsx` 中的 `View` 类型，新增 `'dashboard'`
    - 将默认视图从 `'analyze'` 改为 `'dashboard'`
    - 在侧边栏新增 Dashboard 导航按钮
    - 在 workspace 区域渲染 Dashboard 组件
    - _Requirements: 3.5_

  - [ ]* 3.5 编写 Dashboard 组件单元测试
    - 测试正常数据渲染（stat cards、donut chart、timeline）
    - 测试空状态显示（EmptyDashboard 组件）
    - 测试 API 错误处理
    - Mock API 响应
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 3.6 编写 i18n 属性测试 — Property 12: i18n key completeness
    - **Property 12: i18n key completeness**
    - 使用 fast-check 库
    - 验证 Dashboard 组件引用的每个 locale key 在 zh 和 en 翻译文件中都有非空字符串值
    - **Validates: Requirements 3.6**

- [ ] 4. Checkpoint - Frontend Dashboard 验证
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Burp Extension: Scope Rule 存储与匹配
  - [ ] 5.1 实现 ScopeRuleStore
    - 新建 `burp-extension/src/main/java/com/burpai/core/ScopeRuleStore.java`
    - 使用 Montoya persistence API 持久化 scope rules (JSON 数组)
    - 实现 `getRules()`、`addRule(pattern)`、`removeRule(pattern)` 方法
    - addRule 验证：空字符串或纯空白字符串拒绝并抛出 ValidationException
    - removeRule 允许移除任何 pattern（包括无效的）
    - 支持至少 50 条规则
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ] 5.2 实现 ScopeRuleMatcher
    - 新建 `burp-extension/src/main/java/com/burpai/core/ScopeRuleMatcher.java`
    - 实现自定义 glob 匹配：`*` 匹配单段内字符，`**` 跨段匹配
    - 无 scheme 前缀时同时匹配 http 和 https
    - host 部分大小写不敏感
    - 无规则时所有 URL 均不匹配（auto-analysis 禁用）
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 5.3 编写 ScopeRuleStore 属性测试 — Property 6: Persistence round-trip
    - **Property 6: Scope rule persistence round-trip**
    - 使用 jqwik 库，最少 100 次迭代
    - 验证 add/remove 操作序列后，reload 产生的列表恰好包含已添加且未移除的规则
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [ ]* 5.4 编写 ScopeRuleStore 属性测试 — Property 7: Whitespace rejection
    - **Property 7: Whitespace pattern rejection**
    - 使用 jqwik 库，最少 100 次迭代
    - 验证纯空白字符串（含空字符串）添加被拒绝，现有规则列表不变
    - **Validates: Requirements 4.5**

  - [ ]* 5.5 编写 ScopeRuleMatcher 属性测试 — Property 8: URL matching correctness
    - **Property 8: URL scope matching correctness**
    - 使用 jqwik 库，最少 100 次迭代
    - 验证 URL 匹配至少一个 pattern 时为 in-scope，scheme-agnostic 和 host 大小写不敏感
    - **Validates: Requirements 5.1, 5.3, 5.4**

  - [ ]* 5.6 编写 ScopeRuleMatcher 属性测试 — Property 9: Glob wildcard boundaries
    - **Property 9: Glob wildcard segment boundaries**
    - 使用 jqwik 库，最少 100 次迭代
    - 验证 `*` 不跨越 `.` 或 `/`，`**` 可跨段匹配
    - **Validates: Requirements 5.2**

- [ ] 6. Burp Extension: 自动流量提交
  - [ ] 6.1 实现 SubmissionRateLimiter
    - 新建 `burp-extension/src/main/java/com/burpai/core/SubmissionRateLimiter.java`
    - 实现令牌桶算法，最大 10 次/秒
    - 提供 `tryAcquire()` 方法
    - _Requirements: 6.5_

  - [ ] 6.2 实现 AutoAnalysisProxyListener
    - 新建 `burp-extension/src/main/java/com/burpai/core/AutoAnalysisProxyListener.java`
    - 实现 `ProxyResponseHandler` 接口
    - 在 responseReceived 中：检查启用状态 → ScopeRuleMatcher 匹配 → HttpMessageFilter 过滤静态资源 → RateLimiter 限流 → 异步提交到 BackendClient
    - 使用 ExecutorService 异步提交，不阻塞 Burp proxy 处理
    - Backend 错误时记录日志并继续
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 6.3 编写 RateLimiter 属性测试 — Property 10: Rate limiter enforcement
    - **Property 10: Rate limiter enforcement**
    - 使用 jqwik 库，最少 100 次迭代
    - 验证任意 1 秒滑动窗口内最多 10 次成功获取
    - **Validates: Requirements 6.5**

- [ ] 7. Burp Extension: Proxy History 高亮与任务轮询
  - [ ] 7.1 实现 HighlightManager
    - 新建 `burp-extension/src/main/java/com/burpai/core/HighlightManager.java`
    - 实现 severity-to-color 映射：critical→RED, high→ORANGE, medium→YELLOW, low→BLUE, info→GRAY, failure→MAGENTA
    - 实现 `applyHighlight(HttpRequestResponse, TaskInfo)` 方法
    - 设置颜色高亮和注释（注释失败时继续）
    - 失败任务有 findings 时使用 severity 颜色，无 findings 时使用 MAGENTA
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ] 7.2 实现 TaskPoller
    - 新建 `burp-extension/src/main/java/com/burpai/core/TaskPoller.java`
    - 使用 ScheduledExecutorService，5 秒轮询间隔
    - 维护 pending task_id → HttpRequestResponse 映射
    - 任务完成时调用 HighlightManager
    - 网络错误时记录警告，下次轮询重试
    - _Requirements: 7.5_

  - [ ]* 7.3 编写 HighlightManager 属性测试 — Property 11: Severity-to-color mapping
    - **Property 11: Severity-to-highlight-color mapping**
    - 使用 jqwik 库，最少 100 次迭代
    - 验证高亮颜色对应最高 severity finding，失败无 findings 时为 MAGENTA
    - **Validates: Requirements 7.2, 7.4, 7.5**

- [ ] 8. Checkpoint - Burp Extension 核心组件验证
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Burp Extension: UI 配置面板与集成
  - [ ] 9.1 实现 AutoAnalysisPanel
    - 新建 `burp-extension/src/main/java/com/burpai/core/AutoAnalysisPanel.java`
    - 实现 Swing UI 面板：enable/disable toggle、scope rule 列表、add/remove 控件、session 提交计数器
    - 嵌入现有 Extension panel 的 settings 区域
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ] 9.2 集成 AutoAnalysisEngine 到 Extension 主类
    - 修改 `burp-extension/src/main/java/com/burpai/Extension.java`
    - 在 `initialize()` 中创建 ScopeRuleStore、ScopeRuleMatcher、RateLimiter、ProxyListener、TaskPoller、HighlightManager
    - 注册 ProxyResponseHandler
    - 将 AutoAnalysisPanel 嵌入现有 panel
    - 连接 enable/disable toggle 到 ProxyListener
    - _Requirements: 8.1, 8.2_

  - [ ]* 9.3 编写 AutoAnalysisPanel 单元测试
    - 测试 toggle 状态切换
    - 测试 add/remove scope rule 交互
    - 测试 session 计数器更新
    - _Requirements: 8.1, 8.3, 8.4, 8.5_

- [ ] 10. Final checkpoint - 全部测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Backend 属性测试使用 hypothesis 库，Burp 扩展使用 jqwik 库，Frontend 使用 fast-check 库

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "3.1", "3.2", "5.1"] },
    { "id": 1, "tasks": ["1.2", "3.3", "5.2", "6.1"] },
    { "id": 2, "tasks": ["1.3", "1.4", "1.5", "1.6", "1.7", "1.8", "3.4", "5.3", "5.4", "5.5", "5.6", "6.3"] },
    { "id": 3, "tasks": ["3.5", "3.6", "6.2", "7.1"] },
    { "id": 4, "tasks": ["7.2", "7.3"] },
    { "id": 5, "tasks": ["9.1"] },
    { "id": 6, "tasks": ["9.2", "9.3"] }
  ]
}
```
