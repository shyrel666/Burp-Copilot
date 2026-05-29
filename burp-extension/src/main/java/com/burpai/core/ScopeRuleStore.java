package com.burpai.core;

import java.util.ArrayList;
import java.util.List;

/**
 * Persists auto-analysis scope rules and the enabled flag.
 *
 * Storage is abstracted behind {@link StringStore} so the logic is unit-testable
 * without the Montoya runtime; {@link #montoyaBacked} wires it to Burp's
 * persistence API. Rules are stored as a JSON string array under a single key.
 */
public final class ScopeRuleStore {
    public static final String KEY_RULES = "auto_analysis_scope_rules";
    public static final String KEY_ENABLED = "auto_analysis_enabled";

    /** Minimal key/value string persistence (maps onto Montoya PersistedObject). */
    public interface StringStore {
        String getString(String key);

        void setString(String key, String value);
    }

    public static final class ValidationException extends Exception {
        public ValidationException(String message) {
            super(message);
        }
    }

    private final StringStore store;

    public ScopeRuleStore(StringStore store) {
        this.store = store;
    }

    public List<String> getRules() {
        return decodeArray(store.getString(KEY_RULES));
    }

    public void addRule(String pattern) throws ValidationException {
        if (pattern == null || pattern.trim().isEmpty()) {
            throw new ValidationException("规则不能为空或仅包含空白字符。");
        }
        List<String> rules = getRules();
        String trimmed = pattern.trim();
        if (!rules.contains(trimmed)) {
            rules.add(trimmed);
            store.setString(KEY_RULES, encodeArray(rules));
        }
    }

    public void removeRule(String pattern) {
        List<String> rules = getRules();
        if (rules.remove(pattern)) {
            store.setString(KEY_RULES, encodeArray(rules));
        }
    }

    public boolean isEnabled() {
        return "true".equals(store.getString(KEY_ENABLED));
    }

    public void setEnabled(boolean enabled) {
        store.setString(KEY_ENABLED, enabled ? "true" : "false");
    }

    static String encodeArray(List<String> values) {
        StringBuilder builder = new StringBuilder("[");
        for (int i = 0; i < values.size(); i++) {
            if (i > 0) {
                builder.append(',');
            }
            builder.append('"').append(escape(values.get(i))).append('"');
        }
        return builder.append(']').toString();
    }

    static List<String> decodeArray(String json) {
        List<String> result = new ArrayList<>();
        if (json == null || json.trim().isEmpty()) {
            return result;
        }
        int i = 0;
        while (i < json.length()) {
            if (json.charAt(i) == '"') {
                StringBuilder current = new StringBuilder();
                i++;
                while (i < json.length()) {
                    char c = json.charAt(i);
                    if (c == '\\' && i + 1 < json.length()) {
                        current.append(unescapeChar(json.charAt(i + 1)));
                        i += 2;
                    } else if (c == '"') {
                        i++;
                        break;
                    } else {
                        current.append(c);
                        i++;
                    }
                }
                result.add(current.toString());
            } else {
                i++;
            }
        }
        return result;
    }

    private static char unescapeChar(char escaped) {
        switch (escaped) {
            case 'n': return '\n';
            case 'r': return '\r';
            case 't': return '\t';
            default: return escaped;
        }
    }

    static String escape(String value) {
        if (value == null) {
            return "";
        }
        StringBuilder builder = new StringBuilder();
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"': builder.append("\\\""); break;
                case '\\': builder.append("\\\\"); break;
                case '\n': builder.append("\\n"); break;
                case '\r': builder.append("\\r"); break;
                case '\t': builder.append("\\t"); break;
                default: builder.append(c);
            }
        }
        return builder.toString();
    }
}
