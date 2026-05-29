package com.burpai.core;

import java.net.URI;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Matches request URLs against user-configured glob scope rules.
 *
 * Semantics (see design spec):
 * - {@code *} matches any sequence of characters within a single segment
 *   (does not cross '.' in the host or '/' in the path).
 * - {@code **} matches across segment boundaries.
 * - A pattern without a scheme prefix matches both http and https.
 * - Host comparison is case-insensitive; path comparison is case-sensitive.
 * - A pattern may pin an explicit port (e.g. {@code example.com:8080}); when it
 *   does, the URL must carry that exact explicit port. A pattern without a port
 *   matches any port.
 * - When no rules are configured, nothing is in scope (auto-analysis disabled).
 *
 * The {@link #matches(String, String)} method is pure and unit-tested directly.
 */
public final class ScopeRuleMatcher {
    private final ScopeRuleStore store;

    public ScopeRuleMatcher(ScopeRuleStore store) {
        this.store = store;
    }

    public boolean isInScope(String url) {
        List<String> rules = store.getRules();
        if (rules.isEmpty()) {
            return false;
        }
        for (String rule : rules) {
            if (rule != null && !rule.trim().isEmpty() && matches(rule.trim(), url)) {
                return true;
            }
        }
        return false;
    }

    public static boolean matches(String pattern, String url) {
        if (pattern == null || url == null) {
            return false;
        }
        ParsedUrl target = parseUrl(url);
        if (target == null || target.host == null) {
            return false;
        }

        String patternScheme = null;
        String rest = pattern;
        int schemeIdx = pattern.indexOf("://");
        if (schemeIdx >= 0) {
            patternScheme = pattern.substring(0, schemeIdx);
            rest = pattern.substring(schemeIdx + 3);
        }

        if (patternScheme != null && !patternScheme.equalsIgnoreCase(target.scheme)) {
            return false;
        }

        String patternHost;
        String patternPath;
        int slash = rest.indexOf('/');
        if (slash < 0) {
            patternHost = rest;
            patternPath = null;
        } else {
            patternHost = rest.substring(0, slash);
            patternPath = rest.substring(slash);
        }

        String patternPort = null;
        int colon = patternHost.lastIndexOf(':');
        if (colon >= 0 && colon < patternHost.length() - 1) {
            String maybePort = patternHost.substring(colon + 1);
            if (isAllDigits(maybePort)) {
                patternPort = maybePort;
                patternHost = patternHost.substring(0, colon);
            }
        }

        if (!globMatch(patternHost.toLowerCase(), target.host.toLowerCase(), '.')) {
            return false;
        }
        if (patternPort != null && !patternPort.equals(Integer.toString(target.port))) {
            return false;
        }
        if (patternPath != null) {
            String path = (target.path == null || target.path.isEmpty()) ? "/" : target.path;
            return globMatch(patternPath, path, '/');
        }
        return true;
    }

    static boolean globMatch(String glob, String text, char separator) {
        StringBuilder regex = new StringBuilder("^");
        int i = 0;
        while (i < glob.length()) {
            char c = glob.charAt(i);
            if (c == '*') {
                if (i + 1 < glob.length() && glob.charAt(i + 1) == '*') {
                    regex.append(".*");
                    i += 2;
                } else {
                    // separator is always '.' or '/', both literal inside a character class.
                    // Avoid \Q..\E here: quoting inside [...] is not reliable in Java regex.
                    regex.append("[^").append(separator).append("]*");
                    i++;
                }
            } else {
                regex.append(Pattern.quote(String.valueOf(c)));
                i++;
            }
        }
        regex.append('$');
        return Pattern.compile(regex.toString()).matcher(text).matches();
    }

    private static boolean isAllDigits(String value) {
        if (value.isEmpty()) {
            return false;
        }
        for (int i = 0; i < value.length(); i++) {
            if (!Character.isDigit(value.charAt(i))) {
                return false;
            }
        }
        return true;
    }

    private static ParsedUrl parseUrl(String url) {
        try {
            URI uri = URI.create(url.trim());
            String host = uri.getHost();
            if (host == null) {
                return null;
            }
            return new ParsedUrl(uri.getScheme(), host, uri.getPath(), uri.getPort());
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }

    private static final class ParsedUrl {
        final String scheme;
        final String host;
        final String path;
        final int port;

        ParsedUrl(String scheme, String host, String path, int port) {
            this.scheme = scheme;
            this.host = host;
            this.path = path;
            this.port = port;
        }
    }
}
