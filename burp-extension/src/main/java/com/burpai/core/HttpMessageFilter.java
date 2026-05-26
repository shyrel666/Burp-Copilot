package com.burpai.core;

import java.net.URI;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

public final class HttpMessageFilter {
    public static final int MAX_TOTAL_CHARS = 256 * 1024;
    private static final Set<String> STATIC_EXTENSIONS = new HashSet<>(Arrays.asList(
            ".avif", ".css", ".gif", ".ico", ".jpeg", ".jpg", ".js", ".map", ".png", ".svg", ".webp", ".woff", ".woff2"
    ));

    private HttpMessageFilter() {
    }

    public static PreparedHttpMessage prepare(String requestText, String responseText, String targetUrl) {
        String guardedRequest = requestText == null ? "" : requestText;
        String guardedResponse = responseText;
        boolean requestTruncated = false;
        boolean responseTruncated = false;
        String omittedReason = null;

        if (isStaticResource(targetUrl, guardedRequest)) {
            return new PreparedHttpMessage(
                    guardedRequest,
                    omitBody(guardedResponse, "static resource"),
                    targetUrl,
                    false,
                    false,
                    "static_resource"
            );
        }

        if (hasBinaryBody(guardedRequest) || hasBinaryBody(guardedResponse)) {
            return new PreparedHttpMessage(
                    omitBody(guardedRequest, "binary content"),
                    omitBody(guardedResponse, "binary content"),
                    targetUrl,
                    false,
                    false,
                    "binary"
            );
        }

        int total = guardedRequest.length() + (guardedResponse == null ? 0 : guardedResponse.length());
        if (total > MAX_TOTAL_CHARS) {
            Truncated request = truncate(guardedRequest, MAX_TOTAL_CHARS);
            guardedRequest = request.value;
            requestTruncated = request.truncated;
            int remaining = Math.max(0, MAX_TOTAL_CHARS - guardedRequest.length());
            Truncated response = truncate(guardedResponse, remaining);
            guardedResponse = response.value;
            responseTruncated = response.truncated;
            omittedReason = "too_large";
        }

        return new PreparedHttpMessage(
                guardedRequest,
                guardedResponse,
                targetUrl,
                requestTruncated,
                responseTruncated,
                omittedReason
        );
    }

    private static boolean isStaticResource(String targetUrl, String requestText) {
        String path = pathFromUrl(targetUrl);
        if (path.isEmpty()) {
            String[] lines = requestText.split("\\R", 2);
            String[] parts = lines.length == 0 ? new String[0] : lines[0].split("\\s+");
            path = parts.length >= 2 ? parts[1] : "";
        }
        String normalized = path.toLowerCase();
        int query = normalized.indexOf('?');
        if (query >= 0) {
            normalized = normalized.substring(0, query);
        }
        for (String extension : STATIC_EXTENSIONS) {
            if (normalized.endsWith(extension)) {
                return true;
            }
        }
        return false;
    }

    private static String pathFromUrl(String targetUrl) {
        if (targetUrl == null || targetUrl.trim().isEmpty()) {
            return "";
        }
        try {
            return URI.create(targetUrl).getPath();
        } catch (IllegalArgumentException ignored) {
            return "";
        }
    }

    private static boolean hasBinaryBody(String text) {
        if (text == null) {
            return false;
        }
        String body = splitBody(text);
        for (int i = 0; i < body.length(); i++) {
            char value = body.charAt(i);
            if (value < 32 && value != '\r' && value != '\n' && value != '\t') {
                return true;
            }
        }
        return false;
    }

    private static String omitBody(String text, String reason) {
        if (text == null) {
            return null;
        }
        int split = headerBodySplit(text);
        if (split < 0) {
            return text;
        }
        String separator = text.contains("\r\n\r\n") ? "\r\n\r\n" : "\n\n";
        return text.substring(0, split) + separator + "[body omitted: " + reason + "]";
    }

    private static String splitBody(String text) {
        int split = headerBodySplit(text);
        if (split < 0) {
            return "";
        }
        return text.substring(split + (text.startsWith("\r\n\r\n", split) ? 4 : 2));
    }

    private static int headerBodySplit(String text) {
        int crlf = text.indexOf("\r\n\r\n");
        if (crlf >= 0) {
            return crlf;
        }
        return text.indexOf("\n\n");
    }

    private static Truncated truncate(String text, int limit) {
        if (text == null) {
            return new Truncated(null, false);
        }
        if (text.length() <= limit) {
            return new Truncated(text, false);
        }
        String marker = "\n[truncated: too_large]";
        int cutoff = Math.max(0, limit - marker.length());
        return new Truncated(text.substring(0, cutoff) + marker, true);
    }

    private static final class Truncated {
        private final String value;
        private final boolean truncated;

        private Truncated(String value, boolean truncated) {
            this.value = value;
            this.truncated = truncated;
        }
    }
}
