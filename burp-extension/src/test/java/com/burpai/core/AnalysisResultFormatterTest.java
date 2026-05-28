package com.burpai.core;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class AnalysisResultFormatterTest {

    @Test
    void nullInputReturnsNoResponse() {
        assertEquals("后端无响应。", AnalysisResultFormatter.forDisplay(null));
    }

    @Test
    void emptyInputReturnsNoResponse() {
        assertEquals("后端无响应。", AnalysisResultFormatter.forDisplay(""));
        assertEquals("后端无响应。", AnalysisResultFormatter.forDisplay("   "));
    }

    @Test
    void llmFailedShowsStructuredError() {
        String json = "{\"analysis_id\":\"abc\",\"summary\":\"provider error\",\"findings\":[],"
                + "\"redaction_applied\":false,\"llm_status\":\"failed\"}";
        String result = AnalysisResultFormatter.forDisplay(json);
        assertTrue(result.contains("LLM 分析失败"));
        assertTrue(result.contains("provider error"));
        assertTrue(result.contains("检查提供商设置"));
    }

    @Test
    void successfulAnalysisShowsSummaryAndFindings() {
        String json = "{\"analysis_id\":\"id-123\",\"summary\":\"SQL injection found\","
                + "\"findings\":[{\"title\":\"SQL Injection\",\"severity\":\"high\","
                + "\"confidence\":0.9,\"evidence\":\"id=1' OR '1'='1\","
                + "\"attack_approach\":\"taint input\",\"remediation\":\"use prepared statements\","
                + "\"owasp_category\":\"A03:2021-Injection\"}],"
                + "\"redaction_applied\":true,\"llm_status\":\"ok\"}";
        String result = AnalysisResultFormatter.forDisplay(json);
        assertTrue(result.contains("分析结果"));
        assertTrue(result.contains("id-123"));
        assertTrue(result.contains("SQL injection found"));
        assertTrue(result.contains("发现 #1"));
        assertTrue(result.contains("SQL Injection"));
        assertTrue(result.contains("HIGH"));
        assertTrue(result.contains("0.9"));
        assertTrue(result.contains("A03:2021-Injection"));
        assertTrue(result.contains("1' OR '1'='1"));
        assertTrue(result.contains("use prepared statements"));
        assertTrue(result.contains("分析前已对请求进行脱敏处理"));
    }

    @Test
    void repairedStatusShowsNote() {
        String json = "{\"analysis_id\":\"id-456\",\"summary\":\"XSS found\","
                + "\"findings\":[],\"redaction_applied\":false,\"llm_status\":\"repaired\"}";
        String result = AnalysisResultFormatter.forDisplay(json);
        assertTrue(result.contains("已自动修复"));
    }

    @Test
    void emptyFindingsShowsNoFindingsReported() {
        String json = "{\"analysis_id\":\"id-789\",\"summary\":\"Clean request\","
                + "\"findings\":[],\"redaction_applied\":false,\"llm_status\":\"ok\"}";
        String result = AnalysisResultFormatter.forDisplay(json);
        assertTrue(result.contains("未报告任何发现"));
    }

    @Test
    void multipleFindingsAreNumbered() {
        String json = "{\"analysis_id\":\"id-multi\",\"summary\":\"Multiple issues\","
                + "\"findings\":["
                + "{\"title\":\"Issue A\",\"severity\":\"high\",\"confidence\":0.8,"
                + "\"evidence\":\"ev1\",\"attack_approach\":\"atk1\",\"remediation\":\"fix1\","
                + "\"owasp_category\":\"A01\"},"
                + "{\"title\":\"Issue B\",\"severity\":\"medium\",\"confidence\":0.6,"
                + "\"evidence\":\"ev2\",\"attack_approach\":\"atk2\",\"remediation\":\"fix2\","
                + "\"owasp_category\":null}"
                + "],\"redaction_applied\":false,\"llm_status\":\"ok\"}";
        String result = AnalysisResultFormatter.forDisplay(json);
        assertTrue(result.contains("发现 #1"));
        assertTrue(result.contains("发现 #2"));
        assertTrue(result.contains("Issue A"));
        assertTrue(result.contains("Issue B"));
        assertTrue(result.contains("发现 (2)"));
    }

    @Test
    void unescapeHandlesStandardEscapes() {
        assertEquals("line1\nline2", AnalysisResultFormatter.unescape("line1\\nline2"));
        assertEquals("tab\there", AnalysisResultFormatter.unescape("tab\\there"));
        assertEquals("quote\"here", AnalysisResultFormatter.unescape("quote\\\"here"));
        assertEquals("back\\slash", AnalysisResultFormatter.unescape("back\\\\slash"));
        assertNull(AnalysisResultFormatter.unescape(null));
    }

    @Test
    void unescapeHandlesUnicodeEscapes() {
        assertEquals("\u00e9", AnalysisResultFormatter.unescape("\\u00e9"));
    }

    @Test
    void findingWithNullOwaspCategoryOmitsLine() {
        String json = "{\"analysis_id\":\"id-null\",\"summary\":\"test\","
                + "\"findings\":[{\"title\":\"No OWASP\",\"severity\":\"low\","
                + "\"confidence\":0.3,\"evidence\":\"ev\",\"attack_approach\":\"atk\","
                + "\"remediation\":\"fix\",\"owasp_category\":null}],"
                + "\"redaction_applied\":false,\"llm_status\":\"ok\"}";
        String result = AnalysisResultFormatter.forDisplay(json);
        assertTrue(result.contains("发现 #1"));
        assertFalse(result.contains("OWASP：null"));
    }

    @Test
    void extractFirstReturnsFirstMatch() {
        String input = "\"key\":\"value1\" \"key\":\"value2\"";
        java.util.regex.Pattern pattern = java.util.regex.Pattern.compile("\"key\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
        assertEquals("value1", AnalysisResultFormatter.extractFirst(input, pattern));
    }

    @Test
    void extractFirstReturnsNullWhenNoMatch() {
        String input = "no match here";
        java.util.regex.Pattern pattern = java.util.regex.Pattern.compile("\"key\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
        assertNull(AnalysisResultFormatter.extractFirst(input, pattern));
    }

    @Test
    void truncatedFindingsArrayDoesNotCrash() {
        String json = "{\"analysis_id\":\"x\",\"summary\":\"s\",\"findings\":[";
        String result = AnalysisResultFormatter.forDisplay(json);
        assertNotNull(result);
        assertFalse(result.isEmpty());
    }

    @Test
    void findingsWithNestedObjectsCountCorrectly() {
        String json = "{\"analysis_id\":\"x\",\"summary\":\"s\","
                + "\"findings\":[{\"title\":\"A\",\"severity\":\"high\","
                + "\"confidence\":0.8,\"evidence\":\"e\",\"attack_approach\":\"a\","
                + "\"remediation\":\"r\",\"owasp_category\":{\"nested\":\"key\"}}],"
                + "\"redaction_applied\":false,\"llm_status\":\"ok\"}";
        String result = AnalysisResultFormatter.forDisplay(json);
        assertTrue(result.contains("发现 (1)"), "Should count 1 top-level finding, not count nested braces");
    }

    @Test
    void learnDisplayNullInputReturnsNoResponse() {
        assertEquals("后端无响应。", AnalysisResultFormatter.forLearnDisplay(null));
    }

    @Test
    void learnDisplayFailedShowsLearnError() {
        String json = "{\"analysis_id\":\"abc\",\"summary\":\"provider error\",\"findings\":[],"
                + "\"redaction_applied\":false,\"llm_status\":\"failed\"}";
        String result = AnalysisResultFormatter.forLearnDisplay(json);
        assertTrue(result.contains("学习模式"));
        assertTrue(result.contains("LLM 失败"));
        assertTrue(result.contains("provider error"));
    }

    @Test
    void learnDisplayShowsEducationalLabels() {
        String json = "{\"analysis_id\":\"id-123\",\"summary\":\"SQL injection found\","
                + "\"findings\":[{\"title\":\"SQL Injection\",\"severity\":\"high\","
                + "\"confidence\":0.9,\"evidence\":\"id=1' OR '1'='1\","
                + "\"attack_approach\":\"taint input\",\"remediation\":\"use prepared statements\","
                + "\"owasp_category\":\"A03:2021-Injection\"}],"
                + "\"redaction_applied\":true,\"llm_status\":\"ok\"}";
        String result = AnalysisResultFormatter.forLearnDisplay(json);
        assertTrue(result.contains("学习笔记"));
        assertTrue(result.contains("概述"));
        assertTrue(result.contains("要点 #1"));
        assertTrue(result.contains("概念解释"));
        assertTrue(result.contains("风险等级"));
        assertTrue(result.contains("观察依据"));
        assertTrue(result.contains("验证方式"));
        assertTrue(result.contains("学习建议"));
        assertTrue(result.contains("OWASP 参考"));
        assertTrue(result.contains("脱敏处理"));
        assertFalse(result.contains("发现 #"));
        assertFalse(result.contains("标题："));
        assertFalse(result.contains("证据："));
    }

    @Test
    void learnDisplayEmptyFindingsShowsNormalMessage() {
        String json = "{\"analysis_id\":\"id-789\",\"summary\":\"Clean request\","
                + "\"findings\":[],\"redaction_applied\":false,\"llm_status\":\"ok\"}";
        String result = AnalysisResultFormatter.forLearnDisplay(json);
        assertTrue(result.contains("本次流量正常"));
        assertFalse(result.contains("未报告任何发现"));
    }

    @Test
    void learnDisplayRepairedShowsNote() {
        String json = "{\"analysis_id\":\"id-456\",\"summary\":\"XSS found\","
                + "\"findings\":[],\"redaction_applied\":false,\"llm_status\":\"repaired\"}";
        String result = AnalysisResultFormatter.forLearnDisplay(json);
        assertTrue(result.contains("已自动修复"));
    }
}
