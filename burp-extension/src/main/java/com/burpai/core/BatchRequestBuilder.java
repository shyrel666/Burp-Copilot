package com.burpai.core;

import java.util.List;

/**
 * Builds the JSON body for POST /api/v1/batch/submit from a list of prepared
 * messages, reusing {@link AnalysisRequestBuilder} for each item.
 */
public final class BatchRequestBuilder {
    private BatchRequestBuilder() {
    }

    public static String build(String source, String mode, List<PreparedHttpMessage> messages) {
        StringBuilder builder = new StringBuilder();
        builder.append("{\"items\":[");
        for (int i = 0; i < messages.size(); i++) {
            if (i > 0) {
                builder.append(',');
            }
            builder.append(AnalysisRequestBuilder.build(source, mode, messages.get(i)));
        }
        builder.append("]}");
        return builder.toString();
    }
}
