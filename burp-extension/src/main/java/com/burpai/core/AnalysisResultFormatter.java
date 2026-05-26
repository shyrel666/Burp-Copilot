package com.burpai.core;

public final class AnalysisResultFormatter {
    private AnalysisResultFormatter() {
    }

    public static String forDisplay(String rawJson) {
        if (rawJson == null || rawJson.trim().isEmpty()) {
            return "No response from backend.";
        }
        return rawJson.trim();
    }
}
