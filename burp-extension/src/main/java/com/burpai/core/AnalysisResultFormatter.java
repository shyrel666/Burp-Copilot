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
            return "No response from backend.";
        }

        String llmStatus = extractFirst(rawJson, LLM_STATUS);
        if ("failed".equals(llmStatus)) {
            String summary = unescape(extractFirst(rawJson, SUMMARY));
            StringBuilder sb = new StringBuilder();
            sb.append("=== LLM Analysis Failed ===\n\n");
            if (summary != null && !summary.isEmpty()) {
                sb.append("Reason: ").append(summary).append("\n");
            }
            sb.append("The backend could not get a valid response from the LLM provider.\n");
            sb.append("Check provider settings and health in the dashboard.\n");
            return sb.toString();
        }

        StringBuilder sb = new StringBuilder();
        String analysisId = unescape(extractFirst(rawJson, ANALYSIS_ID));
        String summary = unescape(extractFirst(rawJson, SUMMARY));
        String redaction = extractFirst(rawJson, REDACTION);

        sb.append("=== Analysis Result ===\n\n");
        if (analysisId != null && !analysisId.isEmpty()) {
            sb.append("ID: ").append(analysisId).append("\n");
        }
        if (summary != null && !summary.isEmpty()) {
            sb.append("Summary: ").append(summary).append("\n");
        }
        if ("repaired".equals(llmStatus)) {
            sb.append("(LLM output was repaired from malformed response)\n");
        }
        if ("true".equals(redaction)) {
            sb.append("(Redaction was applied to the request before analysis)\n");
        }

        String findings = extractFindingsSection(rawJson);
        if (findings != null && !findings.trim().isEmpty()) {
            int count = countFindings(findings);
            if (count > 0) {
                sb.append("\n--- Findings (").append(count).append(") ---\n\n");
                formatFindings(findings, sb);
            } else {
                sb.append("\nNo findings reported.\n");
            }
        } else {
            sb.append("\nNo findings reported.\n");
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
                    formatSingleFinding(findingJson, findingNum, sb);
                    findingStart = -1;
                }
            }
        }
    }

    private static void formatSingleFinding(String findingJson, int num, StringBuilder sb) {
        String title = unescape(extractFirst(findingJson, FINDING_TITLE));
        String severity = unescape(extractFirst(findingJson, FINDING_SEVERITY));
        String confidence = extractFirst(findingJson, FINDING_CONFIDENCE);
        String evidence = unescape(extractFirst(findingJson, FINDING_EVIDENCE));
        String attack = unescape(extractFirst(findingJson, FINDING_ATTACK));
        String remediation = unescape(extractFirst(findingJson, FINDING_REMEDIATION));
        String owasp = unescape(extractFirst(findingJson, FINDING_OWASP));

        sb.append("Finding #").append(num).append("\n");
        if (title != null && !title.isEmpty()) {
            sb.append("  Title: ").append(title).append("\n");
        }
        if (severity != null && !severity.isEmpty()) {
            sb.append("  Severity: ").append(severity.toUpperCase());
            if (confidence != null && !confidence.isEmpty()) {
                sb.append(" (confidence: ").append(confidence).append(")");
            }
            sb.append("\n");
        }
        if (owasp != null && !owasp.isEmpty()) {
            sb.append("  OWASP: ").append(owasp).append("\n");
        }
        if (evidence != null && !evidence.isEmpty()) {
            sb.append("  Evidence: ").append(evidence).append("\n");
        }
        if (attack != null && !attack.isEmpty()) {
            sb.append("  Attack approach: ").append(attack).append("\n");
        }
        if (remediation != null && !remediation.isEmpty()) {
            sb.append("  Remediation: ").append(remediation).append("\n");
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
