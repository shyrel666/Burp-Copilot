package com.burpai.core;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class AnalysisRequestBuilderTest {
    @Test
    void buildsDashboardCompatibleJsonWithoutDroppingMetadata() {
        PreparedHttpMessage prepared = new PreparedHttpMessage(
                "GET /profile HTTP/1.1\r\nHost: example.test\r\n\r\n",
                null,
                "https://example.test/profile",
                false,
                false,
                null
        );

        String json = AnalysisRequestBuilder.build("burp", "learn", prepared);

        assertTrue(json.contains("\"source\":\"burp\""));
        assertTrue(json.contains("\"mode\":\"learn\""));
        assertTrue(json.contains("\"content_encoding\":\"utf-8\""));
        assertTrue(json.contains("GET /profile HTTP/1.1"));
    }

    @Test
    void escapesJsonSpecialCharacters() {
        PreparedHttpMessage prepared = new PreparedHttpMessage(
                "POST /quote HTTP/1.1\r\nHost: example.test\r\n\r\n{\"name\":\"alice\"}",
                null,
                null,
                false,
                false,
                null
        );

        String json = AnalysisRequestBuilder.build("burp", "analyze", prepared);

        assertTrue(json.contains("\\\"name\\\":\\\"alice\\\""));
    }
}
