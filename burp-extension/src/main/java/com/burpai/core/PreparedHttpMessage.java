package com.burpai.core;

public class PreparedHttpMessage {
    private final String requestText;
    private final String responseText;
    private final String targetUrl;
    private final boolean requestTruncated;
    private final boolean responseTruncated;
    private final String bodyOmittedReason;

    public PreparedHttpMessage(
            String requestText,
            String responseText,
            String targetUrl,
            boolean requestTruncated,
            boolean responseTruncated,
            String bodyOmittedReason
    ) {
        this.requestText = requestText;
        this.responseText = responseText;
        this.targetUrl = targetUrl;
        this.requestTruncated = requestTruncated;
        this.responseTruncated = responseTruncated;
        this.bodyOmittedReason = bodyOmittedReason;
    }

    public String getRequestText() {
        return requestText;
    }

    public String getResponseText() {
        return responseText;
    }

    public String getTargetUrl() {
        return targetUrl;
    }

    public boolean isRequestTruncated() {
        return requestTruncated;
    }

    public boolean isResponseTruncated() {
        return responseTruncated;
    }

    public String getBodyOmittedReason() {
        return bodyOmittedReason;
    }
}
