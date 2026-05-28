package com.burpai.core;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.regex.Pattern;

public class BackendClient {
    private final String backendUrl;
    private final String backendToken;
    private final int connectTimeoutMillis;
    private final int readTimeoutMillis;

    public BackendClient(String backendUrl, String backendToken) {
        this(backendUrl, backendToken, 5000, 120000);
    }

    BackendClient(String backendUrl, String backendToken, int connectTimeoutMillis, int readTimeoutMillis) {
        this.backendUrl = stripTrailingSlash(backendUrl == null || backendUrl.trim().isEmpty()
                ? "http://localhost:8000"
                : backendUrl.trim());
        this.backendToken = backendToken == null ? "" : backendToken.trim();
        this.connectTimeoutMillis = connectTimeoutMillis;
        this.readTimeoutMillis = readTimeoutMillis;
    }

    public String analyze(String json) throws IOException {
        return post("/api/v1/analyze", json);
    }

    public void analyzeStream(String json, StreamCallback callback) throws IOException {
        HttpURLConnection connection = open("/api/v1/analyze/stream");
        try {
            connection.setRequestMethod("POST");
            connection.setDoOutput(true);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setRequestProperty("Accept", "text/event-stream");
            connection.setReadTimeout(0);
            byte[] body = json.getBytes(StandardCharsets.UTF_8);
            connection.setRequestProperty("Content-Length", Integer.toString(body.length));
            try (OutputStream output = connection.getOutputStream()) {
                output.write(body);
            }
            int status = connection.getResponseCode();
            if (status < 200 || status >= 300) {
                InputStream errorStream = connection.getErrorStream();
                String errorBody = readAll(errorStream);
                callback.onError(new IOException("Backend returned HTTP " + status + ": " + errorBody));
                return;
            }
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8))) {
                String eventName = "";
                StringBuilder dataBuilder = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    if (Thread.interrupted()) {
                        callback.onError(new InterruptedException("Stream reading interrupted"));
                        return;
                    }
                    if (line.isEmpty()) {
                        if (eventName != null && !eventName.isEmpty() && dataBuilder.length() > 0) {
                            handleSseEvent(eventName, dataBuilder.toString(), callback);
                        }
                        eventName = "";
                        dataBuilder.setLength(0);
                        continue;
                    }
                    if (line.startsWith("event: ")) {
                        eventName = line.substring("event: ".length());
                    } else if (line.startsWith("data: ")) {
                        if (dataBuilder.length() > 0) {
                            dataBuilder.append('\n');
                        }
                        dataBuilder.append(line.substring("data: ".length()));
                    }
                }
                if (eventName != null && !eventName.isEmpty() && dataBuilder.length() > 0) {
                    handleSseEvent(eventName, dataBuilder.toString(), callback);
                }
            } catch (IOException e) {
                callback.onError(e);
            }
        } finally {
            connection.disconnect();
        }
    }

    private void handleSseEvent(String eventName, String data, StreamCallback callback) {
        switch (eventName) {
            case "status":
                String statusValue = extractJsonStringField(data, "status");
                if (statusValue != null) {
                    callback.onStatus(statusValue);
                }
                break;
            case "content":
                String text = extractJsonStringField(data, "text");
                if (text != null) {
                    callback.onContent(text);
                }
                break;
            case "result":
                String analysis = extractJsonObjectField(data, "analysis");
                if (analysis != null) {
                    callback.onResult(analysis);
                }
                break;
            default:
                break;
        }
    }

    static String extractJsonStringField(String json, String fieldName) {
        String key = "\"" + fieldName + "\"\\s*:\\s*\"";
        Pattern pattern = Pattern.compile(key + "((?:[^\"\\\\]|\\\\.)*)\"");
        java.util.regex.Matcher matcher = pattern.matcher(json);
        if (matcher.find()) {
            return AnalysisResultFormatter.unescape(matcher.group(1));
        }
        return null;
    }

    static String extractJsonObjectField(String json, String fieldName) {
        String key = "\"" + fieldName + "\"\\s*:";
        Pattern pattern = Pattern.compile(key);
        java.util.regex.Matcher matcher = pattern.matcher(json);
        if (!matcher.find()) {
            return null;
        }
        int start = matcher.end();
        while (start < json.length() && Character.isWhitespace(json.charAt(start))) {
            start++;
        }
        if (start >= json.length() || json.charAt(start) != '{') {
            return null;
        }
        int depth = 0;
        boolean inString = false;
        boolean escape = false;
        int i = start;
        while (i < json.length()) {
            char c = json.charAt(i);
            if (escape) {
                escape = false;
            } else if (c == '\\') {
                escape = true;
            } else if (c == '"') {
                inString = !inString;
            } else if (!inString) {
                if (c == '{') depth++;
                else if (c == '}') {
                    depth--;
                    if (depth == 0) {
                        return json.substring(start, i + 1);
                    }
                }
            }
            i++;
        }
        return null;
    }

    public boolean health() throws IOException {
        String response = get("/api/v1/health");
        return response.contains("\"ok\"") || response.contains("ok");
    }

    private String post(String path, String json) throws IOException {
        HttpURLConnection connection = open(path);
        connection.setRequestMethod("POST");
        connection.setDoOutput(true);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        byte[] body = json.getBytes(StandardCharsets.UTF_8);
        connection.setRequestProperty("Content-Length", Integer.toString(body.length));
        try (OutputStream output = connection.getOutputStream()) {
            output.write(body);
        }
        return readResponse(connection);
    }

    private String get(String path) throws IOException {
        HttpURLConnection connection = open(path);
        connection.setRequestMethod("GET");
        return readResponse(connection);
    }

    private HttpURLConnection open(String path) throws IOException {
        URL url = new URL(backendUrl + path);
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setConnectTimeout(connectTimeoutMillis);
        connection.setReadTimeout(readTimeoutMillis);
        connection.setRequestProperty("Accept", "application/json");
        if (!backendToken.isEmpty()) {
            connection.setRequestProperty("X-Backend-Token", backendToken);
        }
        return connection;
    }

    private String readResponse(HttpURLConnection connection) throws IOException {
        int status = connection.getResponseCode();
        InputStream stream = status >= 200 && status < 300
                ? connection.getInputStream()
                : connection.getErrorStream();
        String body = readAll(stream);
        if (status < 200 || status >= 300) {
            throw new IOException("Backend returned HTTP " + status + ": " + body);
        }
        return body;
    }

    private String readAll(InputStream stream) throws IOException {
        if (stream == null) {
            return "";
        }
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            StringBuilder builder = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                if (builder.length() > 0) {
                    builder.append('\n');
                }
                builder.append(line);
            }
            return builder.toString();
        }
    }

    private static String stripTrailingSlash(String value) {
        while (value.endsWith("/")) {
            value = value.substring(0, value.length() - 1);
        }
        return value;
    }
}
