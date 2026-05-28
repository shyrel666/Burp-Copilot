package com.burpai.core;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class BackendClientStreamTest {

    @Test
    void extractJsonStringFieldFindsSimpleValue() {
        String json = "{\"status\":\"calling_provider\"}";
        assertEquals("calling_provider", BackendClient.extractJsonStringField(json, "status"));
    }

    @Test
    void extractJsonStringFieldReturnsNullForMissingField() {
        String json = "{\"other\":\"value\"}";
        assertNull(BackendClient.extractJsonStringField(json, "status"));
    }

    @Test
    void extractJsonStringFieldHandlesEscapedChars() {
        String json = "{\"text\":\"line1\\nline2\"}";
        assertEquals("line1\nline2", BackendClient.extractJsonStringField(json, "text"));
    }

    @Test
    void extractJsonStringFieldHandlesCompactJson() {
        String json = "{\"status\":\"redacting\"}";
        assertEquals("redacting", BackendClient.extractJsonStringField(json, "status"));
    }

    @Test
    void extractJsonObjectFieldFindsNestedObject() {
        String json = "{\"analysis\":{\"summary\":\"ok\",\"findings\":[]}}";
        String result = BackendClient.extractJsonObjectField(json, "analysis");
        assertNotNull(result);
        assertTrue(result.contains("\"summary\""));
        assertTrue(result.contains("\"findings\""));
    }

    @Test
    void extractJsonObjectFieldReturnsNullForMissingField() {
        String json = "{\"other\":\"value\"}";
        assertNull(BackendClient.extractJsonObjectField(json, "analysis"));
    }

    @Test
    void extractJsonObjectFieldHandlesNestedBraces() {
        String json = "{\"analysis\":{\"findings\":[{\"title\":\"x\"}]}}";
        String result = BackendClient.extractJsonObjectField(json, "analysis");
        assertNotNull(result);
        assertTrue(result.contains("\"findings\""));
    }

    @Test
    void extractJsonObjectFieldHandlesEscapedQuotes() {
        String json = "{\"analysis\":{\"summary\":\"He said \\\"hello\\\"\"}}";
        String result = BackendClient.extractJsonObjectField(json, "analysis");
        assertNotNull(result);
        assertTrue(result.contains("hello"));
    }
}
