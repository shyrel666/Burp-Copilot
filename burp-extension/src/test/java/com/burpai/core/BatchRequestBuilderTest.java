package com.burpai.core;

import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;

class BatchRequestBuilderTest {

    @Test
    void wrapsItemsInBatchEnvelope() {
        List<PreparedHttpMessage> messages = Arrays.asList(
                new PreparedHttpMessage("GET /a HTTP/1.1\r\nHost: x.test\r\n\r\n", null, "https://x.test/a", false, false, null),
                new PreparedHttpMessage("GET /b HTTP/1.1\r\nHost: x.test\r\n\r\n", null, "https://x.test/b", false, false, null)
        );

        String json = BatchRequestBuilder.build("burp", "recon", messages);

        assertTrue(json.startsWith("{\"items\":["));
        assertTrue(json.endsWith("]}"));
        assertTrue(json.contains("\"source\":\"burp\""));
        assertTrue(json.contains("\"mode\":\"recon\""));
        assertTrue(json.contains("https://x.test/a"));
        assertTrue(json.contains("https://x.test/b"));
    }
}
