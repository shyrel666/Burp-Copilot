package com.burpai.core;

import java.util.ArrayList;
import java.util.List;

/**
 * Pure helpers for reading fields out of backend JSON responses (task status
 * and analysis findings). Kept separate from {@link BackendClient} so the
 * parsing logic can be unit-tested without any network or Montoya runtime.
 *
 * <p>The analysis JSON returned by {@code GET /api/v1/analysis/{id}} embeds the
 * redacted raw request/response text, which may itself contain JSON with
 * {@code "severity"} or {@code "summary"} keys. A naive regex over the whole
 * payload would mistake those for the real fields and mis-color/mis-label the
 * Proxy History entry. The extractors below therefore walk the JSON while
 * respecting string and escape boundaries, so a token is only treated as a key
 * when it is a structural key (immediately followed by {@code :}); string
 * values are consumed whole and never tokenized.
 */
public final class BackendResponseParser {
    private BackendResponseParser() {
    }

    public static String taskStatus(String taskJson) {
        return BackendClient.extractJsonStringField(taskJson, "status");
    }

    public static String taskAnalysisId(String taskJson) {
        return BackendClient.extractJsonStringField(taskJson, "analysis_id");
    }

    public static String summary(String analysisJson) {
        List<String> values = stringValuesForKey(analysisJson, "summary", true);
        return values.isEmpty() ? null : values.get(0);
    }

    public static List<String> severities(String analysisJson) {
        return stringValuesForKey(analysisJson, "severity", false);
    }

    /**
     * Scans {@code json} respecting string/escape boundaries and returns the
     * string value(s) assigned to {@code key}. Only a quoted token immediately
     * followed by {@code :} is treated as a key, so {@code "severity"} or
     * {@code "summary"} appearing inside a JSON string value (e.g. embedded,
     * escaped traffic) is ignored.
     */
    static List<String> stringValuesForKey(String json, String key, boolean firstOnly) {
        List<String> out = new ArrayList<>();
        if (json == null) {
            return out;
        }
        int n = json.length();
        int i = 0;
        while (i < n) {
            if (json.charAt(i) == '"') {
                StringBuilder rawToken = new StringBuilder();
                i = readRawString(json, i, rawToken);
                int colon = skipWhitespace(json, i);
                if (colon < n && json.charAt(colon) == ':' && key.equals(rawToken.toString())) {
                    int valueStart = skipWhitespace(json, colon + 1);
                    if (valueStart < n && json.charAt(valueStart) == '"') {
                        StringBuilder rawValue = new StringBuilder();
                        readRawString(json, valueStart, rawValue);
                        out.add(AnalysisResultFormatter.unescape(rawValue.toString()));
                        if (firstOnly) {
                            return out;
                        }
                    }
                }
            } else {
                i++;
            }
        }
        return out;
    }

    /**
     * Reads a JSON string starting at the opening-quote index, appending the raw
     * (still-escaped) content to {@code rawOut}, and returns the index just past
     * the closing quote. Escaped characters (including {@code \"}) are preserved
     * verbatim so they neither terminate the scan nor lose information before the
     * final {@link AnalysisResultFormatter#unescape} pass.
     */
    private static int readRawString(String json, int openQuote, StringBuilder rawOut) {
        int n = json.length();
        int i = openQuote + 1;
        while (i < n) {
            char c = json.charAt(i);
            if (c == '\\' && i + 1 < n) {
                rawOut.append(c).append(json.charAt(i + 1));
                i += 2;
            } else if (c == '"') {
                return i + 1;
            } else {
                rawOut.append(c);
                i++;
            }
        }
        return i;
    }

    private static int skipWhitespace(String json, int from) {
        int i = from;
        while (i < json.length() && Character.isWhitespace(json.charAt(i))) {
            i++;
        }
        return i;
    }
}
