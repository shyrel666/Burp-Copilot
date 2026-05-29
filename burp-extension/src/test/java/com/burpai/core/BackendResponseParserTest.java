package com.burpai.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

class BackendResponseParserTest {

    @Test
    void readsTaskStatusAndAnalysisId() {
        String task = "{\"task_id\":\"t1\",\"status\":\"done\",\"analysis_id\":\"a-123\"}";
        assertEquals("done", BackendResponseParser.taskStatus(task));
        assertEquals("a-123", BackendResponseParser.taskAnalysisId(task));
    }

    @Test
    void extractsAllSeveritiesFromAnalysis() {
        String analysis = "{\"summary\":\"s\",\"findings\":[" +
                "{\"title\":\"t\",\"severity\":\"high\"}," +
                "{\"title\":\"u\",\"severity\":\"critical\"}]}";
        List<String> severities = BackendResponseParser.severities(analysis);
        assertEquals(2, severities.size());
        assertTrue(severities.contains("high"));
        assertTrue(severities.contains("critical"));
        assertEquals("s", BackendResponseParser.summary(analysis));
    }

    @Test
    void emptyFindingsYieldNoSeverities() {
        assertTrue(BackendResponseParser.severities("{\"summary\":\"ok\",\"findings\":[]}").isEmpty());
    }

    @Test
    void ignoresSeverityAndSummaryInsideRedactedTraffic() {
        // The analysis JSON embeds redacted request/response text whose escaped
        // body itself contains "severity"/"summary" keys. Those must not leak
        // into the real field extraction (regression for highlight pollution).
        String analysis = "{"
                + "\"analysis_id\":\"a-1\","
                + "\"request_text\":\"POST /x\\r\\n\\r\\n{\\\"severity\\\":\\\"critical\\\"}\","
                + "\"response_text\":\"HTTP/1.1 200\\r\\n\\r\\n{\\\"summary\\\":\\\"injected\\\"}\","
                + "\"summary\":\"真实摘要\","
                + "\"findings\":[{\"title\":\"t\",\"severity\":\"low\"}]"
                + "}";

        List<String> severities = BackendResponseParser.severities(analysis);
        assertEquals(1, severities.size());
        assertEquals("low", severities.get(0));
        assertEquals("真实摘要", BackendResponseParser.summary(analysis));
    }

    @Test
    void summaryBeforeRawTrafficStillResolvesToRealField() {
        // Even when summary precedes the embedded traffic, an injected summary
        // inside the request body must be ignored.
        String analysis = "{"
                + "\"summary\":\"真实摘要\","
                + "\"request_text\":\"GET /\\r\\n\\r\\n{\\\"summary\\\":\\\"fake\\\"}\","
                + "\"findings\":[]"
                + "}";
        assertEquals("真实摘要", BackendResponseParser.summary(analysis));
    }
}
