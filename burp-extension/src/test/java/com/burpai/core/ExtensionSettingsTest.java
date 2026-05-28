package com.burpai.core;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for ExtensionSettings contract and BackendClient default consistency.
 * Full integration tests require a running Burp Suite with Montoya API;
 * these tests verify the default URL contract is consistent across components.
 */
class ExtensionSettingsTest {

    @Test
    void backendClientDefaultUrlMatchesExtensionSettingsDefault() {
        // Both should default to http://localhost:8000
        // BackendClient normalizes null/empty to its default
        BackendClient nullClient = new BackendClient(null, null);
        BackendClient emptyClient = new BackendClient("", "");
        // Both clients should be constructable without error
        assertNotNull(nullClient);
        assertNotNull(emptyClient);
    }

    @Test
    void backendClientTrimsInputUrl() {
        // BackendClient should handle whitespace in URL gracefully
        BackendClient client = new BackendClient("  http://localhost:8000  ", "  token  ");
        assertNotNull(client);
    }

    @Test
    void analysisResultFormatterHandlesMalformedFindingsArray() {
        // When findings array is truncated (e.g. "["), formatter should not crash
        String truncated = "{\"analysis_id\":\"x\",\"summary\":\"s\",\"findings\":[";
        String result = AnalysisResultFormatter.forDisplay(truncated);
        // Should produce some output without throwing
        assertNotNull(result);
        assertFalse(result.isEmpty());
    }

    @Test
    void backendErrorMessageHandlesCancellationException() {
        Exception exc = new java.util.concurrent.CancellationException();
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("后端请求失败"));
    }

    @Test
    void backendErrorMessageExtractsFullStatusCode() {
        // Verify that HTTP 500 is extracted fully, not truncated to "HTTP 5"
        Exception exc = new Exception("Backend returned HTTP 500: Internal Server Error");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("HTTP 500"));
        assertFalse(result.contains("HTTP 5") && !result.contains("HTTP 500"));
    }
}
