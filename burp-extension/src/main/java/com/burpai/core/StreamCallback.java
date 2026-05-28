package com.burpai.core;

public interface StreamCallback {
    void onStatus(String status);
    void onContent(String text);
    void onResult(String rawJson);
    void onError(Exception e);
}
