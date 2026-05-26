package com.burpai.core;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class BackendErrorMessageTest {

    @Test
    void timeoutErrorShowsActionableMessage() {
        Exception exc = new Exception("java.net.SocketTimeoutException: Read timed out");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("timed out"));
        assertTrue(result.contains("Ollama is running locally"));
        assertTrue(result.contains("Provider health check"));
    }

    @Test
    void connectTimeoutShowsActionableMessage() {
        Exception exc = new Exception("java.net.SocketTimeoutException: connect timed out");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("timed out"));
    }

    @Test
    void auth401ErrorShowsTokenGuidance() {
        Exception exc = new Exception("Backend returned HTTP 401: Unauthorized");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("Authentication failed"));
        assertTrue(result.contains("Backend Token"));
        assertTrue(result.contains("BACKEND_TOKEN"));
    }

    @Test
    void auth403ErrorShowsTokenGuidance() {
        Exception exc = new Exception("Backend returned HTTP 403: Forbidden");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("Authentication failed"));
    }

    @Test
    void notFound404ShowsEndpointGuidance() {
        Exception exc = new Exception("Backend returned HTTP 404: Not Found");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("not found"));
        assertTrue(result.contains("Backend URL"));
    }

    @Test
    void connectionRefusedShowsUnreachableMessage() {
        Exception exc = new Exception("java.net.ConnectException: Connection refused");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("unreachable"));
        assertTrue(result.contains("backend server is running"));
    }

    @Test
    void serverError5xxShowsServerError() {
        Exception exc = new Exception("Backend returned HTTP 500: Internal Server Error");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("server error"));
        assertTrue(result.contains("backend logs"));
    }

    @Test
    void malformedJsonResponseShowsParseError() {
        Exception exc = new Exception("not valid JSON at position 0");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("Malformed response"));
    }

    @Test
    void genericErrorShowsMessage() {
        Exception exc = new Exception("Something unexpected happened");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("Backend request failed"));
        assertTrue(result.contains("Something unexpected happened"));
    }

    @Test
    void nullMessageUsesClassName() {
        Exception exc = new RuntimeException((String) null);
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("Backend request failed"));
    }

    @Test
    void serverError500ExtractsFullStatusCode() {
        Exception exc = new Exception("Backend returned HTTP 500: Internal Server Error");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("HTTP 500"), "Should contain full status code 'HTTP 500'");
        assertFalse(result.contains("HTTP 5") && !result.contains("HTTP 500"),
                "Should not contain truncated 'HTTP 5' without the full code");
    }

    @Test
    void serverError502ExtractsFullStatusCode() {
        Exception exc = new Exception("Backend returned HTTP 502: Bad Gateway");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("HTTP 502"));
    }
}
