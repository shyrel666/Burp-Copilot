package com.burpai.core;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class BackendClient {
    private final String backendUrl;
    private final String backendToken;
    private final int connectTimeoutMillis;
    private final int readTimeoutMillis;

    public BackendClient(String backendUrl, String backendToken) {
        this(backendUrl, backendToken, 5000, 45000);
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
