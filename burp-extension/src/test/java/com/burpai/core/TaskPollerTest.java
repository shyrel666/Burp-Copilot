package com.burpai.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class TaskPollerTest {

    private static final class StubFetcher implements TaskPoller.TaskFetcher {
        String analysis;

        @Override
        public String getTask(String taskId) {
            return null;
        }

        @Override
        public String getAnalysis(String analysisId) {
            return analysis;
        }
    }

    @Test
    void runningTaskIsNotTerminal() throws Exception {
        TaskPoller.Resolution r = TaskPoller.resolve("{\"status\":\"running\"}", new StubFetcher());
        assertFalse(r.terminal);
    }

    @Test
    void doneTaskHighlightsBySeverity() throws Exception {
        StubFetcher fetcher = new StubFetcher();
        fetcher.analysis = "{\"summary\":\"发现越权\",\"findings\":[{\"severity\":\"high\"}]}";
        TaskPoller.Resolution r = TaskPoller.resolve(
                "{\"status\":\"done\",\"analysis_id\":\"a1\"}", fetcher);
        assertTrue(r.terminal);
        assertTrue(r.highlight);
        assertEquals(HighlightPalette.ORANGE, r.colorKey);
        assertEquals("发现越权", r.notes);
    }

    @Test
    void failedTaskWithoutAnalysisIsMagenta() throws Exception {
        TaskPoller.Resolution r = TaskPoller.resolve("{\"status\":\"failed\"}", new StubFetcher());
        assertTrue(r.terminal);
        assertTrue(r.highlight);
        assertEquals(HighlightPalette.MAGENTA, r.colorKey);
    }

    @Test
    void cancelledTaskIsTerminalWithoutHighlight() throws Exception {
        TaskPoller.Resolution r = TaskPoller.resolve("{\"status\":\"cancelled\"}", new StubFetcher());
        assertTrue(r.terminal);
        assertFalse(r.highlight);
    }
}
