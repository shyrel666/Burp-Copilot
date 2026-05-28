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
            return "后端请求超时。\n\n"
                    + "通常意味着 LLM 提供商响应缓慢或不可达。\n"
                    + "请检查：\n"
                    + "  1. 后端 URL 和 Token 是否正确\n"
                    + "  2. 提供商 API 密钥是否已在后端配置（或 Ollama 是否在本地运行）\n"
                    + "  3. 网络是否能访问提供商端点\n"
                    + "  4. 控制面板中提供商健康检查是否通过";
        }

        if (containsAny(message, "HTTP 401", "401 Unauthorized", "HTTP 403", "403 Forbidden")) {
            return "认证失败（HTTP 401/403）。\n\n"
                    + "后端拒绝了请求。请检查：\n"
                    + "  1. 后端 Token 是否与后端 .env 中的 BACKEND_TOKEN 一致\n"
                    + "  2. Token 中是否包含多余的空格或换行符";
        }

        if (containsAny(message, "HTTP 404", "404 Not Found")) {
            return "后端端点未找到（HTTP 404）。\n\n"
                    + "后端 URL 可能不正确，或后端版本不匹配。\n"
                    + "请确认后端 URL 指向本项目正在运行的后端实例。";
        }

        if (containsAny(message, "ConnectException", "Connection refused", "Connection timed out", "No route to host")) {
            return "无法连接后端。\n\n"
                    + "无法建立到后端的连接。请检查：\n"
                    + "  1. 后端服务是否正在运行\n"
                    + "  2. 后端 URL 是否正确（默认：http://localhost:8000）\n"
                    + "  3. 防火墙是否阻止了连接";
        }

        if (containsAny(message, "HTTP 5")) {
            return "后端服务器错误（" + extractHttpStatus(message) + "）。\n\n"
                    + "后端遇到内部错误，请查看后端日志了解详情。";
        }

        if (containsAny(message, "JsonException", "JSONException", "SyntaxError", "not valid JSON", "Unexpected character")) {
            return "后端返回了格式错误的响应。\n\n"
                    + "后端返回的数据无法解析。\n"
                    + "请检查后端日志，并确保后端版本与扩展匹配。";
        }

        return "后端请求失败：" + message;
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
