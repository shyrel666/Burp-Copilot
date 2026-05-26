package com.burpai.core;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class AnalysisResultFormatterTest {

    @Test
    void nullInputReturnsNoResponse() {
        assertEquals("No response from backend.", AnalysisResultFormatter.forDisplay(null));
    }

    @Test
    void emptyInputReturnsNoResponse() {
        assertEquals("No response from backend.", AnalysisResultFormatter.forDisplay(""));
        assertEquals("No response from backend.", AnalysisResultFormatter.forDisplay("   "));
    }

    @Test
    void llmFailedShowsStructuredError() {
        String json = "{\"analysis_id\":\"abc\",\"summary\":\"provider error\",\"findings\":[],"
                + "\"redaction_applied\":false,\"llm_status\":\"failed\"}";
        String result = AnalysisResultFormatter.forDisplay(json);
        assertTrue(result.contains("LLM Analysis Failed"));
        assertTrue(result.contains("provider error"));
        assertTrue(result.contains("Check provider settings"));
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
        assertTrue(result.contains("Analysis Result"));
        assertTrue(result.contains("id-123"));
        assertTrue(result.contains("SQL injection found"));
        assertTrue(result.contains("Finding #1"));
        assertTrue(result.contains("SQL Injection"));
        assertTrue(result.contains("HIGH"));
        assertTrue(result.contains("0.9"));
        assertTrue(result.contains("A03:2021-Injection"));
        assertTrue(result.contains("1' OR '1'='1"));
        assertTrue(result.contains("use prepared statements"));
        assertTrue(result.contains("Redaction was applied"));
    }

    @Test
    void repairedStatusShowsNote() {
        String json = "{\"analysis_id\":\"id-456\",\"summary\":\"XSS found\","
                + "\"findings\":[],\"redaction_applied\":false,\"llm_status\":\"repaired\"}";
        String result = AnalysisResultFormatter.forDisplay(json);
        assertTrue(result.contains("repaired from malformed response"));
    }

    @Test
    void emptyFindingsShowsNoFindingsReported() {
        String json = "{\"analysis_id\":\"id-789\",\"summary\":\"Clean request\","
                + "\"findings\":[],\"redaction_applied\":false,\"llm_status\":\"ok\"}";
        String result = AnalysisResultFormatter.forDisplay(json);
        assertTrue(result.contains("No findings reported"));
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
        assertTrue(result.contains("Finding #1"));
        assertTrue(result.contains("Finding #2"));
        assertTrue(result.contains("Issue A"));
        assertTrue(result.contains("Issue B"));
        assertTrue(result.contains("Findings (2)"));
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
        assertTrue(result.contains("Finding #1"));
        assertFalse(result.contains("OWASP: null"));
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
        assertTrue(result.contains("Findings (1)"), "Should count 1 top-level finding, not count nested braces");
    }
}
