package com.burpai.core;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class BackendErrorMessageTest {

    @Test
    void timeoutErrorShowsActionableMessage() {
        Exception exc = new Exception("java.net.SocketTimeoutException: Read timed out");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("超时"));
        assertTrue(result.contains("Ollama"));
        assertTrue(result.contains("健康检查"));
    }

    @Test
    void connectTimeoutShowsActionableMessage() {
        Exception exc = new Exception("java.net.SocketTimeoutException: connect timed out");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("超时"));
    }

    @Test
    void auth401ErrorShowsTokenGuidance() {
        Exception exc = new Exception("Backend returned HTTP 401: Unauthorized");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("认证失败"));
        assertTrue(result.contains("Token"));
        assertTrue(result.contains("BACKEND_TOKEN"));
    }

    @Test
    void auth403ErrorShowsTokenGuidance() {
        Exception exc = new Exception("Backend returned HTTP 403: Forbidden");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("认证失败"));
    }

    @Test
    void notFound404ShowsEndpointGuidance() {
        Exception exc = new Exception("Backend returned HTTP 404: Not Found");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("未找到"));
        assertTrue(result.contains("URL"));
    }

    @Test
    void connectionRefusedShowsUnreachableMessage() {
        Exception exc = new Exception("java.net.ConnectException: Connection refused");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("无法连接"));
        assertTrue(result.contains("后端服务是否正在运行"));
    }

    @Test
    void serverError5xxShowsServerError() {
        Exception exc = new Exception("Backend returned HTTP 500: Internal Server Error");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("服务器错误"));
        assertTrue(result.contains("后端日志"));
    }

    @Test
    void malformedJsonResponseShowsParseError() {
        Exception exc = new Exception("not valid JSON at position 0");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("格式错误"));
    }

    @Test
    void genericErrorShowsMessage() {
        Exception exc = new Exception("Something unexpected happened");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("后端请求失败"));
        assertTrue(result.contains("Something unexpected happened"));
    }

    @Test
    void nullMessageUsesClassName() {
        Exception exc = new RuntimeException((String) null);
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("后端请求失败"));
    }

    @Test
    void serverError500ExtractsFullStatusCode() {
        Exception exc = new Exception("Backend returned HTTP 500: Internal Server Error");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("HTTP 500"), "Should contain full status code 'HTTP 500'");
    }

    @Test
    void serverError502ExtractsFullStatusCode() {
        Exception exc = new Exception("Backend returned HTTP 502: Bad Gateway");
        String result = BackendErrorMessage.forException(exc);
        assertTrue(result.contains("HTTP 502"));
    }
}
