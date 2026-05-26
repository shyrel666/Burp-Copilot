package com.burpai.core;

import burp.api.montoya.MontoyaApi;

/**
 * Persists extension settings (backend URL and backend token) across Burp restarts
 * using the Montoya persistence API. Falls back to defaults when no saved values exist.
 */
public final class ExtensionSettings {
    private static final String KEY_BACKEND_URL = "backend_url";
    private static final String KEY_BACKEND_TOKEN = "backend_token";
    private static final String DEFAULT_BACKEND_URL = "http://localhost:8000";
    private static final String DEFAULT_BACKEND_TOKEN = "";

    private final MontoyaApi api;

    public ExtensionSettings(MontoyaApi api) {
        this.api = api;
    }

    public String getBackendUrl() {
        String saved = api.persistence().extensionData().getString(KEY_BACKEND_URL);
        if (saved != null) {
            saved = saved.trim();
        }
        return (saved != null && !saved.isEmpty()) ? saved : DEFAULT_BACKEND_URL;
    }

    public void setBackendUrl(String url) {
        api.persistence().extensionData().setString(KEY_BACKEND_URL, url == null ? "" : url);
    }

    public String getBackendToken() {
        String saved = api.persistence().extensionData().getString(KEY_BACKEND_TOKEN);
        return saved != null ? saved : DEFAULT_BACKEND_TOKEN;
    }

    public void setBackendToken(String token) {
        api.persistence().extensionData().setString(KEY_BACKEND_TOKEN, token == null ? "" : token);
    }

    public String getDefaultBackendUrl() {
        return DEFAULT_BACKEND_URL;
    }

    public String getDefaultBackendToken() {
        return DEFAULT_BACKEND_TOKEN;
    }
}
