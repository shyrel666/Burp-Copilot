package com.burpai.core;

/**
 * Formats structured, user-readable error messages for common backend failure states.
 * Keeps messages actionable without exposing secrets or raw traffic.
 */
public final class BackendErrorMessage {
    private BackendErrorMessage() {
    }

    public static String forException(Exception exc) {
        String message = exc.getMessage() != null ? exc.getMessage() : exc.getClass().getSimpleName();

        if (containsAny(message, "SocketTimeoutException", "timed out", "Read timed out", "connect timed out")) {
            return "Backend request timed out.\n\n"
                    + "This usually means the LLM provider is slow or unreachable.\n"
                    + "Check:\n"
                    + "  1. Backend URL and token are correct\n"
                    + "  2. Provider API key is configured in backend .env (or Ollama is running locally)\n"
                    + "  3. Network can reach the provider endpoint\n"
                    + "  4. Provider health check passes in the dashboard";
        }

        if (containsAny(message, "HTTP 401", "401 Unauthorized", "HTTP 403", "403 Forbidden")) {
            return "Authentication failed (HTTP 401/403).\n\n"
                    + "The backend rejected the request. Check:\n"
                    + "  1. Backend Token matches the BACKEND_TOKEN in the backend .env\n"
                    + "  2. The token does not contain extra whitespace or line breaks";
        }

        if (containsAny(message, "HTTP 404", "404 Not Found")) {
            return "Backend endpoint not found (HTTP 404).\n\n"
                    + "The backend URL may be incorrect or the backend version is mismatched.\n"
                    + "Verify the Backend URL points to a running instance of this project's backend.";
        }

        if (containsAny(message, "ConnectException", "Connection refused", "Connection timed out", "No route to host")) {
            return "Backend is unreachable.\n\n"
                    + "Could not connect to the backend. Check:\n"
                    + "  1. The backend server is running\n"
                    + "  2. The Backend URL is correct (default: http://localhost:8000)\n"
                    + "  3. No firewall is blocking the connection";
        }

        if (containsAny(message, "HTTP 5")) {
            return "Backend server error (" + extractHttpStatus(message) + ").\n\n"
                    + "The backend encountered an internal error. Check the backend logs for details.";
        }

        if (containsAny(message, "JsonException", "JSONException", "SyntaxError", "not valid JSON", "Unexpected character")) {
            return "Malformed response from backend.\n\n"
                    + "The backend returned data that could not be parsed.\n"
                    + "Check the backend logs and ensure the backend version matches the extension.";
        }

        return "Backend request failed: " + message;
    }

    private static boolean containsAny(String haystack, String... needles) {
        for (String needle : needles) {
            if (haystack.contains(needle)) {
                return true;
            }
        }
        return false;
    }

    private static String extractHttpStatus(String message) {
        int idx = message.indexOf("HTTP ");
        if (idx >= 0) {
            int codeStart = idx + 5;
            int codeEnd = codeStart;
            while (codeEnd < message.length() && Character.isDigit(message.charAt(codeEnd))) {
                codeEnd++;
            }
            if (codeEnd > codeStart) {
                return "HTTP " + message.substring(codeStart, codeEnd);
            }
        }
        return "5xx";
    }
}
