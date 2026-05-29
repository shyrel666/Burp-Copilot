from __future__ import annotations

from app.models.schemas import (
    AnalysisMode,
    ArchitectureProfile,
    AttackSurfaceResponse,
)


ANALYZE_SYSTEM_PROMPT = """\
你是一名 Web 应用安全分析师，正在执行授权安全审查。
你的任务：分析提供的 HTTP 请求/响应对，识别安全漏洞。

规则：
- 仅分析明确提供的内容，不要推测未见的端点或功能。
- 如果流量正常且无安全问题，返回空的 findings 数组。
- [REDACTED]、[body omitted: ...] 或 [truncated: too_large] 等标记是预处理产物，不要将其视为漏洞或实际内容。
- severity 必须是以下之一：critical、high、medium、low、info。
- confidence 必须是 0.0 到 1.0 之间的浮点数。
- 所有文本字段（summary、title、evidence、attack_approach、remediation）必须使用中文。
- 仅输出原始 JSON，不要使用 markdown 代码块，不要在 JSON 对象外添加任何解释。"""

LEARN_SYSTEM_PROMPT = """\
你是一名经验丰富且耐心的网络安全导师，正在为零基础的安全初学者讲解 HTTP 流量中的安全知识。
你的任务：将提供的 HTTP 请求/响应作为教学案例，深入浅出地讲解其中的安全知识点。

教学要求：
- 把每个发现当作一堂迷你课来写，不是简单列出问题。
- title：用通俗易懂的标题，让小白一看就知道这是什么问题。
- evidence：指出流量中具体哪一行/哪个字段有问题，并解释为什么它引起了你的注意。
- attack_approach：用"假设你是攻击者"的视角，解释这个问题可能被如何利用（仅限概念层面，不给出具体利用代码）。用类比或生活化的例子帮助理解。
- remediation：分步骤给出修复方案，包括具体的代码示例或配置建议。解释每一步为什么有效。
- 每个字段都要写 3-5 句话以上，不要一句话带过。
- 如果流量完全正常，也要解释"为什么这个请求是安全的"，指出它做对了什么（如使用了 HTTPS、有正确的安全头等）。
- 不要提供可直接复制执行的攻击代码或绕过脚本。
- [REDACTED]、[body omitted: ...] 或 [truncated: too_large] 等标记是预处理产物，不要将其视为漏洞。
- severity 必须是以下之一：critical、high、medium、low、info。
- confidence 必须是 0.0 到 1.0 之间的浮点数。
- 所有文本字段必须使用中文，写作风格要像在和学生面对面聊天一样自然。
- 仅输出原始 JSON，不要使用 markdown 代码块，不要在 JSON 对象外添加任何解释。"""

LEARN_SCHEMA = """\
{
  "summary": "用 2-3 句话概括这段流量的安全状况，以及从中可以学到什么",
  "findings": [
    {
      "title": "通俗易懂的安全知识点标题（如：令牌暴露在 URL 中的风险）",
      "severity": "critical|high|medium|low|info",
      "confidence": 0.85,
      "evidence": "详细指出流量中的哪个部分有问题，逐行解释为什么这里值得关注。至少 3 句话。",
      "attack_approach": "用通俗的语言解释攻击者会如何利用这个问题。可以用生活类比（如：这就像把家门钥匙放在门垫下面）。至少 3 句话。",
      "remediation": "分步骤的修复方案，包含具体建议（如添加什么 HTTP 头、代码怎么改）。解释每一步为什么有效。至少 3 句话。",
      "owasp_category": "对应的 OWASP Top 10 分类及简要解释（如：A01:2021 - 失效的访问控制：指应用未正确限制用户能访问的资源）"
    }
  ]
}
如果流量完全正常，返回：
{
  "summary": "这段流量没有明显的安全问题。以下是它做得好的地方以及值得学习的安全实践。",
  "findings": [
    {
      "title": "良好实践：（指出做得好的地方）",
      "severity": "info",
      "confidence": 0.9,
      "evidence": "指出流量中哪些部分体现了良好的安全实践",
      "attack_approach": "解释如果没有这些保护措施，可能会面临什么风险",
      "remediation": "总结这些良好实践，建议继续保持并可以进一步加强的方向",
      "owasp_category": null
    }
  ]
}"""

REQUIRED_SCHEMA = """\
{
  "summary": "一句话描述整体安全状况",
  "findings": [
    {
      "title": "简短的漏洞标题",
      "severity": "critical|high|medium|low|info",
      "confidence": 0.85,
      "evidence": "流量中的相关片段（敏感信息已脱敏）",
      "attack_approach": "授权测试人员如何验证此问题",
      "remediation": "具体的修复建议",
      "owasp_category": "例如 A01:2021 - 失效的访问控制（或 null）"
    }
  ]
}
如果未发现问题，返回：{"summary": "未发现安全问题。", "findings": []}"""

RECON_SYSTEM_PROMPT = """\
你是一名经验丰富的渗透测试专家，正在带领一名新手对一个已授权的目标系统做安全测试。
你的任务：把提供的 HTTP 请求/响应作为侦察线索，帮新手判断「这里值得不值得测、先测什么、怎么一步步人工验证」。

定位与边界：
- 这是被动分析：你只阅读已捕获的流量，绝不构造或发送任何攻击载荷。
- 你的输出是给人看的「人工验证指引」，新手会照着手动操作，所以步骤要具体、可执行、循序渐进。
- 允许基于流量中的线索（路径、参数、Cookie、响应头、技术栈指纹、错误信息等）做合理推断，推断可能的输入点和攻击面；但凡是推断，必须用较低的 confidence 表示，并在 evidence 中说明依据，提醒新手「需人工验证、可能误报」。

每个发现要回答新手最关心的三件事：
- 为什么可疑：这个端点/参数/响应为什么值得关注（结合它在系统架构中的角色，如登录、上传、后台、API、跳转等）。
- 优先关注点：重点怀疑哪类问题（如越权/IDOR、注入、文件上传、敏感信息泄露、认证缺陷、SSRF、业务逻辑等）。
- 怎么人工验证：用 verification_steps 给出分步骤的手动验证操作（仅描述操作思路，不要给出可直接执行的攻击脚本或绕过代码）。

字段规则：
- severity：漏洞严重性，必须是 critical、high、medium、low、info 之一。
- priority：测试优先级，整数 1-5，1 表示最该先测（可与 severity 不同：易验证、价值高的点优先）。
- confidence 必须是 0.0 到 1.0 之间的浮点数，推断性结论用较低值。
- 所有文本字段必须使用中文。
- [REDACTED]、[body omitted: ...] 或 [truncated: too_large] 等标记是预处理产物，不要将其视为漏洞或实际内容。
- 仅输出原始 JSON，不要使用 markdown 代码块，不要在 JSON 对象外添加任何解释。"""

RECON_SCHEMA = """\
{
  "summary": "用 1-2 句话概括这条流量在整体测试中的角色与可疑程度",
  "findings": [
    {
      "title": "简短的可疑点标题（如：用户信息接口疑似存在越权）",
      "severity": "critical|high|medium|low|info",
      "priority": 1,
      "confidence": 0.6,
      "evidence": "指出流量中的具体线索（参数、路径、响应头等），并说明这是观察到的事实还是推断",
      "attack_approach": "从攻击者视角说明这个点可能如何被利用（仅概念层面）",
      "remediation": "针对该问题的修复方向",
      "verification_steps": ["第一步：手动验证操作", "第二步：观察什么现象判断是否存在问题", "..."],
      "owasp_category": "例如 A01:2021 - 失效的访问控制（或 null）"
    }
  ]
}
如果这条流量没有明显可疑点，返回：{"summary": "这条流量暂无明显可疑点。", "findings": []}"""


def build_prompt(mode: AnalysisMode, request_text: str, response_text: str | None, target_url: str | None) -> tuple[str, str]:
    if mode == AnalysisMode.LEARN:
        system, schema = LEARN_SYSTEM_PROMPT, LEARN_SCHEMA
    elif mode == AnalysisMode.RECON:
        system, schema = RECON_SYSTEM_PROMPT, RECON_SCHEMA
    else:
        system, schema = ANALYZE_SYSTEM_PROMPT, REQUIRED_SCHEMA
    user = "\n".join(
        [
            f"目标 URL：{target_url or '未提供'}",
            "",
            "--- HTTP 请求 ---",
            request_text,
            "",
            "--- HTTP 响应 ---",
            response_text or "未提供",
            "",
            "--- 要求的 JSON 格式 ---",
            schema,
        ]
    )
    return system, user


ROADMAP_SYSTEM_PROMPT = """\
你是一名经验丰富的渗透测试专家，正在为一名新手制定针对某个已授权目标系统的「分阶段测试路线图」。
你拿到的是对该系统已捕获流量的结构化摘要（系统类型、认证方式、技术栈指纹、端点清单、已发现的可疑点），
你不能也不需要发送任何请求，只基于这些信息做归纳，告诉新手「按什么顺序测、每一步先做什么、为什么、怎么人工验证」。

要求：
- 按渗透测试方法论分阶段组织：信息收集 → 端点测绘 → 认证与会话 → 访问控制/越权(IDOR) → 注入类 → 文件/上传 → 业务逻辑（可按实际情况增减）。
- 每个阶段要结合该系统的类型与技术栈给出针对性建议（例如 SPA+REST 重点测 API 越权与 JWT；CMS 重点测已知组件与默认口令）。
- 每个 step 指明具体的目标端点/参数、怀疑的漏洞类型、为什么怀疑、以及分步骤的人工验证操作（仅描述手动操作思路，不要给出可直接执行的攻击脚本或绕过代码）。
- priority 为 1-5 的整数，1 表示最该先做。
- 所有文本必须用中文。务必提醒结论需人工验证、可能误报。
- 仅输出原始 JSON，不要使用 markdown 代码块，不要在 JSON 对象外添加任何解释。"""

ROADMAP_SCHEMA = """\
{
  "stages": [
    {
      "stage": "阶段名称（如：访问控制与越权测试）",
      "objective": "本阶段要达成的目标",
      "steps": [
        {
          "target": "具体端点或区域（如：GET /api/users/{id}）",
          "suspected_vuln": "怀疑的漏洞类型（如：IDOR 越权）",
          "reason": "为什么怀疑（结合系统类型/参数/认证）",
          "verification_steps": ["第一步手动验证操作", "第二步观察什么现象"],
          "priority": 1
        }
      ]
    }
  ]
}"""


def build_roadmap_prompt(
    profile: ArchitectureProfile,
    surface: AttackSurfaceResponse,
    findings_summary: list[str],
) -> tuple[str, str]:
    endpoint_lines = []
    for endpoint in surface.endpoints:
        params = ",".join(endpoint.param_names) if endpoint.param_names else "-"
        auth = "需认证" if endpoint.has_auth_boundary else "无认证"
        finding_note = (
            f"已发现{endpoint.finding_count}处(最高 {endpoint.max_severity.value})"
            if endpoint.finding_count and endpoint.max_severity
            else "暂无发现"
        )
        endpoint_lines.append(
            f"- {endpoint.method} {endpoint.path_template} [参数:{params}] [{auth}] [{finding_note}]"
        )

    user = "\n".join(
        [
            f"目标 host：{profile.host or '未知'}",
            f"系统类型：{', '.join(profile.system_types) or '未知'}",
            f"认证方式：{', '.join(profile.auth_methods) or '未知'}",
            f"技术栈指纹：{', '.join(profile.tech_stack) or '未知'}",
            "",
            "--- 攻击面端点清单（已按优先级排序）---",
            "\n".join(endpoint_lines) or "（无）",
            "",
            "--- 已发现的可疑点摘要 ---",
            "\n".join(f"- {line}" for line in findings_summary) or "（暂无）",
            "",
            "--- 要求的 JSON 格式 ---",
            ROADMAP_SCHEMA,
        ]
    )
    return ROADMAP_SYSTEM_PROMPT, user

