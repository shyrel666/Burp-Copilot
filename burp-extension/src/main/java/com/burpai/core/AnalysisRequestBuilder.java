package com.burpai.core;

public final class AnalysisRequestBuilder {
    private AnalysisRequestBuilder() {
    }

    public static String build(String source, String mode, PreparedHttpMessage message) {
        StringBuilder builder = new StringBuilder();
        builder.append('{');
        field(builder, "source", source);
        comma(builder);
        field(builder, "mode", mode);
        comma(builder);
        field(builder, "request_text", message.getRequestText());
        comma(builder);
        nullableField(builder, "response_text", message.getResponseText());
        comma(builder);
        nullableField(builder, "target_url", message.getTargetUrl());
        comma(builder);
        builder.append("\"metadata\":{");
        field(builder, "content_encoding", "utf-8");
        comma(builder);
        booleanField(builder, "request_truncated", message.isRequestTruncated());
        comma(builder);
        booleanField(builder, "response_truncated", message.isResponseTruncated());
        comma(builder);
        nullableField(builder, "body_omitted_reason", message.getBodyOmittedReason());
        builder.append("}}");
        return builder.toString();
    }

    private static void field(StringBuilder builder, String name, String value) {
        builder.append('"').append(name).append("\":\"").append(escape(value)).append('"');
    }

    private static void nullableField(StringBuilder builder, String name, String value) {
        builder.append('"').append(name).append("\":");
        if (value == null) {
            builder.append("null");
        } else {
            builder.append('"').append(escape(value)).append('"');
        }
    }

    private static void booleanField(StringBuilder builder, String name, boolean value) {
        builder.append('"').append(name).append("\":").append(value);
    }

    private static void comma(StringBuilder builder) {
        builder.append(',');
    }

    static String escape(String value) {
        if (value == null) {
            return "";
        }
        StringBuilder escaped = new StringBuilder();
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"':
                    escaped.append("\\\"");
                    break;
                case '\\':
                    escaped.append("\\\\");
                    break;
                case '\b':
                    escaped.append("\\b");
                    break;
                case '\f':
                    escaped.append("\\f");
                    break;
                case '\n':
                    escaped.append("\\n");
                    break;
                case '\r':
                    escaped.append("\\r");
                    break;
                case '\t':
                    escaped.append("\\t");
                    break;
                default:
                    if (c < 32) {
                        escaped.append(String.format("\\u%04x", (int) c));
                    } else {
                        escaped.append(c);
                    }
            }
        }
        return escaped.toString();
    }
}
