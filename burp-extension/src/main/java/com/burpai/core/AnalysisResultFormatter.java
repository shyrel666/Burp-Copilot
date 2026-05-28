package com.burpai.core;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Formats the backend's AnalysisResponse JSON into a human-readable summary
 * displayed in the Burp extension result area.
 *
 * Expected backend schema:
 *   analysis_id, summary, findings[{title,severity,confidence,evidence,
 *   attack_approach,remediation,owasp_category}], redaction_applied, llm_status
 */
public final class AnalysisResultFormatter {
    private static final Pattern SUMMARY = Pattern.compile("\"summary\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
    private static final Pattern LLM_STATUS = Pattern.compile("\"llm_status\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
    private static final Pattern REDACTION = Pattern.compile("\"redaction_applied\"\\s*:\\s*(true|false)");
    private static final Pattern ANALYSIS_ID = Pattern.compile("\"analysis_id\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
    private static final Pattern FINDINGS_ARRAY = Pattern.compile("\"findings\"\\s*:\\s*\\[");
    private static final Pattern FINDING_TITLE = Pattern.compile("\"title\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
    private static final Pattern FINDING_SEVERITY = Pattern.compile("\"severity\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
    private static final Pattern FINDING_CONFIDENCE = Pattern.compile("\"confidence\"\\s*:\\s*([0-9.]+)");
    private static final Pattern FINDING_EVIDENCE = Pattern.compile("\"evidence\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
    private static final Pattern FINDING_REMEDIATION = Pattern.compile("\"remediation\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
    private static final Pattern FINDING_ATTACK = Pattern.compile("\"attack_approach\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
    private static final Pattern FINDING_OWASP = Pattern.compile("\"owasp_category\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
    private AnalysisResultFormatter() {
    }

    public static String forDisplay(String rawJson) {
        if (rawJson == null || rawJson.trim().isEmpty()) {
            return "后端无响应。";
        }

        String llmStatus = extractFirst(rawJson, LLM_STATUS);
        if ("failed".equals(llmStatus)) {
            String summary = unescape(extractFirst(rawJson, SUMMARY));
            StringBuilder sb = new StringBuilder();
            sb.append("=== LLM 分析失败 ===\n\n");
            if (summary != null && !summary.isEmpty()) {
                sb.append("原因：").append(summary).append("\n");
            }
            sb.append("后端无法从 LLM 提供商获取有效响应。\n");
            sb.append("请在控制面板中检查提供商设置和健康状态。\n");
            return sb.toString();
        }

        StringBuilder sb = new StringBuilder();
        String analysisId = unescape(extractFirst(rawJson, ANALYSIS_ID));
        String summary = unescape(extractFirst(rawJson, SUMMARY));
        String redaction = extractFirst(rawJson, REDACTION);

        sb.append("=== 分析结果 ===\n\n");
        if (analysisId != null && !analysisId.isEmpty()) {
            sb.append("ID：").append(analysisId).append("\n");
        }
        if (summary != null && !summary.isEmpty()) {
            sb.append("摘要：").append(summary).append("\n");
        }
        if ("repaired".equals(llmStatus)) {
            sb.append("（LLM 输出格式异常，已自动修复）\n");
        }
        if ("true".equals(redaction)) {
            sb.append("（分析前已对请求进行脱敏处理）\n");
        }

        String findings = extractFindingsSection(rawJson);
        if (findings != null && !findings.trim().isEmpty()) {
            int count = countFindings(findings);
            if (count > 0) {
                sb.append("\n--- 发现 (").append(count).append(") ---\n\n");
                formatFindings(findings, sb);
            } else {
                sb.append("\n未报告任何发现。\n");
            }
        } else {
            sb.append("\n未报告任何发现。\n");
        }

        return sb.toString();
    }

    public static String forLearnDisplay(String rawJson) {
        if (rawJson == null || rawJson.trim().isEmpty()) {
            return "后端无响应。";
        }

        String llmStatus = extractFirst(rawJson, LLM_STATUS);
        if ("failed".equals(llmStatus)) {
            String summary = unescape(extractFirst(rawJson, SUMMARY));
            StringBuilder sb = new StringBuilder();
            sb.append("=== 学习模式 — LLM 失败 ===\n\n");
            if (summary != null && !summary.isEmpty()) {
                sb.append("原因：").append(summary).append("\n");
            }
            sb.append("后端无法从 LLM 提供商获取有效响应。\n");
            sb.append("请在控制面板中检查提供商设置和健康状态。\n");
            return sb.toString();
        }

        StringBuilder sb = new StringBuilder();
        String summary = unescape(extractFirst(rawJson, SUMMARY));
        String redaction = extractFirst(rawJson, REDACTION);

        sb.append("=== 学习笔记 ===\n\n");
        if (summary != null && !summary.isEmpty()) {
            sb.append("概述：").append(summary).append("\n");
        }
        if ("repaired".equals(llmStatus)) {
            sb.append("（LLM 输出格式异常，已自动修复）\n");
        }
        if ("true".equals(redaction)) {
            sb.append("（分析前已对请求进行脱敏处理）\n");
        }

        String findings = extractFindingsSection(rawJson);
        if (findings != null && !findings.trim().isEmpty()) {
            int count = countFindings(findings);
            if (count > 0) {
                sb.append("\n--- 学习要点 (").append(count).append(") ---\n\n");
                formatLearnFindings(findings, sb);
            } else {
                sb.append("\n本次流量正常，无安全风险要点。\n");
            }
        } else {
            sb.append("\n本次流量正常，无安全风险要点。\n");
        }

        return sb.toString();
    }

    static String extractFirst(String input, Pattern pattern) {
        Matcher m = pattern.matcher(input);
        return m.find() ? m.group(1) : null;
    }

    private static String extractFindingsSection(String rawJson) {
        Matcher m = FINDINGS_ARRAY.matcher(rawJson);
        if (!m.find()) {
            return null;
        }
        int start = m.end();
        int depth = 1;
        int i = start;
        boolean inString = false;
        boolean escape = false;
        while (i < rawJson.length() && depth > 0) {
            char c = rawJson.charAt(i);
            if (escape) {
                escape = false;
            } else if (c == '\\') {
                escape = true;
            } else if (c == '"') {
                inString = !inString;
            } else if (!inString) {
                if (c == '[') {
                    depth++;
                } else if (c == ']') {
                    depth--;
                }
            }
            i++;
        }
        int end = i - 1;
        if (end < start) {
            return null;
        }
        return rawJson.substring(start, end);
    }

    private static int countFindings(String findingsSection) {
        int count = 0;
        int depth = 0;
        boolean inString = false;
        boolean escape = false;
        for (int i = 0; i < findingsSection.length(); i++) {
            char c = findingsSection.charAt(i);
            if (escape) {
                escape = false;
                continue;
            }
            if (c == '\\') {
                escape = true;
                continue;
            }
            if (c == '"') {
                inString = !inString;
                continue;
            }
            if (inString) {
                continue;
            }
            if (c == '{') {
                if (depth == 0) {
                    count++;
                }
                depth++;
            } else if (c == '}') {
                depth--;
            }
        }
        return count;
    }

    private static void formatFindings(String findingsSection, StringBuilder sb) {
        walkFindings(findingsSection, (findingJson, num) -> formatSingleFinding(findingJson, num, sb));
    }

    private static void formatSingleFinding(String findingJson, int num, StringBuilder sb) {
        String title = unescape(extractFirst(findingJson, FINDING_TITLE));
        String severity = unescape(extractFirst(findingJson, FINDING_SEVERITY));
        String confidence = extractFirst(findingJson, FINDING_CONFIDENCE);
        String evidence = unescape(extractFirst(findingJson, FINDING_EVIDENCE));
        String attack = unescape(extractFirst(findingJson, FINDING_ATTACK));
        String remediation = unescape(extractFirst(findingJson, FINDING_REMEDIATION));
        String owasp = unescape(extractFirst(findingJson, FINDING_OWASP));

        sb.append("发现 #").append(num).append("\n");
        if (title != null && !title.isEmpty()) {
            sb.append("  标题：").append(title).append("\n");
        }
        if (severity != null && !severity.isEmpty()) {
            sb.append("  严重性：").append(severity.toUpperCase());
            if (confidence != null && !confidence.isEmpty()) {
                sb.append("（置信度：").append(confidence).append("）");
            }
            sb.append("\n");
        }
        if (owasp != null && !owasp.isEmpty()) {
            sb.append("  OWASP：").append(owasp).append("\n");
        }
        if (evidence != null && !evidence.isEmpty()) {
            sb.append("  证据：").append(evidence).append("\n");
        }
        if (attack != null && !attack.isEmpty()) {
            sb.append("  攻击方式：").append(attack).append("\n");
        }
        if (remediation != null && !remediation.isEmpty()) {
            sb.append("  修复建议：").append(remediation).append("\n");
        }
        sb.append("\n");
    }

    private static void formatLearnFindings(String findingsSection, StringBuilder sb) {
        walkFindings(findingsSection, (findingJson, num) -> formatSingleLearnFinding(findingJson, num, sb));
    }

    @FunctionalInterface
    private interface FindingHandler {
        void handle(String findingJson, int num);
    }

    private static void walkFindings(String findingsSection, FindingHandler handler) {
        int depth = 0;
        boolean inString = false;
        boolean escape = false;
        int findingStart = -1;
        int findingNum = 0;

        for (int i = 0; i < findingsSection.length(); i++) {
            char c = findingsSection.charAt(i);
            if (escape) {
                escape = false;
                continue;
            }
            if (c == '\\') {
                escape = true;
                continue;
            }
            if (c == '"') {
                inString = !inString;
                continue;
            }
            if (inString) {
                continue;
            }
            if (c == '{') {
                if (depth == 0) {
                    findingStart = i;
                }
                depth++;
            } else if (c == '}') {
                depth--;
                if (depth == 0 && findingStart >= 0) {
                    findingNum++;
                    String findingJson = findingsSection.substring(findingStart, i + 1);
                    handler.handle(findingJson, findingNum);
                    findingStart = -1;
                }
            }
        }
    }

    private static void formatSingleLearnFinding(String findingJson, int num, StringBuilder sb) {
        String title = unescape(extractFirst(findingJson, FINDING_TITLE));
        String severity = unescape(extractFirst(findingJson, FINDING_SEVERITY));
        String confidence = extractFirst(findingJson, FINDING_CONFIDENCE);
        String evidence = unescape(extractFirst(findingJson, FINDING_EVIDENCE));
        String attack = unescape(extractFirst(findingJson, FINDING_ATTACK));
        String remediation = unescape(extractFirst(findingJson, FINDING_REMEDIATION));
        String owasp = unescape(extractFirst(findingJson, FINDING_OWASP));

        sb.append("要点 #").append(num).append("\n");
        if (title != null && !title.isEmpty()) {
            sb.append("  概念解释：").append(title).append("\n");
        }
        if (severity != null && !severity.isEmpty()) {
            sb.append("  风险等级：").append(severity.toUpperCase());
            if (confidence != null && !confidence.isEmpty()) {
                sb.append("（置信度：").append(confidence).append("）");
            }
            sb.append("\n");
        }
        if (owasp != null && !owasp.isEmpty()) {
            sb.append("  OWASP 参考：").append(owasp).append("\n");
        }
        if (evidence != null && !evidence.isEmpty()) {
            sb.append("  观察依据：").append(evidence).append("\n");
        }
        if (attack != null && !attack.isEmpty()) {
            sb.append("  验证方式：").append(attack).append("\n");
        }
        if (remediation != null && !remediation.isEmpty()) {
            sb.append("  学习建议：").append(remediation).append("\n");
        }
        sb.append("\n");
    }

    static String unescape(String value) {
        if (value == null) {
            return null;
        }
        StringBuilder sb = new StringBuilder(value.length());
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c == '\\' && i + 1 < value.length()) {
                char next = value.charAt(i + 1);
                switch (next) {
                    case '"': sb.append('"'); i++; break;
                    case '\\': sb.append('\\'); i++; break;
                    case 'n': sb.append('\n'); i++; break;
                    case 'r': sb.append('\r'); i++; break;
                    case 't': sb.append('\t'); i++; break;
                    case 'b': sb.append('\b'); i++; break;
                    case 'f': sb.append('\f'); i++; break;
                    case 'u':
                        if (i + 5 < value.length()) {
                            String hex = value.substring(i + 2, i + 6);
                            try {
                                sb.append((char) Integer.parseInt(hex, 16));
                                i += 5;
                            } catch (NumberFormatException e) {
                                sb.append(c);
                            }
                        } else {
                            sb.append(c);
                        }
                        break;
                    default: sb.append(c); break;
                }
            } else {
                sb.append(c);
            }
        }
        return sb.toString();
    }
}
