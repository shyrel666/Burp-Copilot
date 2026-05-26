package com.burpai.core;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class HttpMessageFilterTest {
    @Test
    void staticResourceKeepsResponseHeadersAndOmitsBody() {
        PreparedHttpMessage prepared = HttpMessageFilter.prepare(
                "GET /assets/banner.webp HTTP/1.1\r\nHost: example.test\r\n\r\n",
                "HTTP/1.1 200 OK\r\nContent-Type: image/webp\r\n\r\nbinary-image-body",
                "https://example.test/assets/banner.webp"
        );

        assertTrue(prepared.getResponseText().contains("HTTP/1.1 200 OK"));
        assertTrue(prepared.getResponseText().contains("Content-Type: image/webp"));
        assertFalse(prepared.getResponseText().contains("binary-image-body"));
        assertEquals("static_resource", prepared.getBodyOmittedReason());
    }

    @Test
    void binaryBodyIsOmitted() {
        PreparedHttpMessage prepared = HttpMessageFilter.prepare(
                "POST /upload HTTP/1.1\r\nHost: example.test\r\n\r\nhello\u0000world",
                null,
                "https://example.test/upload"
        );

        assertFalse(prepared.getRequestText().contains("\u0000"));
        assertEquals("binary", prepared.getBodyOmittedReason());
    }

    @Test
    void oversizedPayloadIsTruncated() {
        StringBuilder builder = new StringBuilder("POST /submit HTTP/1.1\r\nHost: example.test\r\n\r\n");
        for (int i = 0; i < 270 * 1024; i++) {
            builder.append('A');
        }

        PreparedHttpMessage prepared = HttpMessageFilter.prepare(builder.toString(), null, "https://example.test/submit");

        assertTrue(prepared.isRequestTruncated());
        assertTrue(prepared.getRequestText().length() <= 256 * 1024);
        assertEquals("too_large", prepared.getBodyOmittedReason());
    }
}
