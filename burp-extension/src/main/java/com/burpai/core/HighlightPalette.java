package com.burpai.core;

import java.util.List;

/**
 * Pure decision logic for Proxy History highlight color, independent of the
 * Montoya {@code HighlightColor} enum so it can be unit-tested.
 *
 * Rules:
 * - Color follows the highest-severity finding: critical=red, high=orange,
 *   medium=yellow, low=blue, info=gray.
 * - A failed task with no findings is magenta.
 * - A failed task that still produced findings uses the severity color.
 */
public final class HighlightPalette {
    public static final String RED = "red";
    public static final String ORANGE = "orange";
    public static final String YELLOW = "yellow";
    public static final String BLUE = "blue";
    public static final String GRAY = "gray";
    public static final String MAGENTA = "magenta";

    private HighlightPalette() {
    }

    public static String colorKeyFor(List<String> severities, boolean taskFailed) {
        String highest = highestSeverity(severities);
        if (highest == null) {
            return taskFailed ? MAGENTA : GRAY;
        }
        switch (highest) {
            case "critical": return RED;
            case "high": return ORANGE;
            case "medium": return YELLOW;
            case "low": return BLUE;
            default: return GRAY;
        }
    }

    private static String highestSeverity(List<String> severities) {
        if (severities == null || severities.isEmpty()) {
            return null;
        }
        int best = -1;
        String result = null;
        for (String severity : severities) {
            int rank = rank(severity);
            if (rank > best) {
                best = rank;
                result = severity == null ? null : severity.toLowerCase();
            }
        }
        return result;
    }

    private static int rank(String severity) {
        if (severity == null) {
            return -1;
        }
        switch (severity.toLowerCase()) {
            case "critical": return 5;
            case "high": return 4;
            case "medium": return 3;
            case "low": return 2;
            case "info": return 1;
            default: return 0;
        }
    }
}
