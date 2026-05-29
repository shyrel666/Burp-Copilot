package com.burpai.core;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.core.Annotations;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.http.message.requests.HttpRequest;
import burp.api.montoya.http.message.responses.HttpResponse;

import java.util.Collections;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;

/**
 * Coordinates passive auto-analysis: scope matching, rate limiting, asynchronous
 * batch submission, completion polling, and Proxy History highlighting. No
 * payloads are ever sent; only already-captured traffic is submitted to the
 * backend (which performs redaction).
 */
public final class AutoAnalysisEngine {
    private static final String SOURCE = "burp";
    private static final String MODE = "recon";

    private final MontoyaApi api;
    private final ScopeRuleStore store;
    private final ScopeRuleMatcher matcher;
    private final SubmissionRateLimiter rateLimiter = new SubmissionRateLimiter();
    private final ExecutorService executor;
    private final TaskPoller poller;
    private final Supplier<BackendClient> clientSupplier;
    private final AtomicInteger sessionCount = new AtomicInteger();
    private volatile Runnable onCountChanged;

    public AutoAnalysisEngine(MontoyaApi api, ScopeRuleStore store, ExtensionSettings settings) {
        this.api = api;
        this.store = store;
        this.matcher = new ScopeRuleMatcher(store);
        this.executor = Executors.newFixedThreadPool(2, runnable -> {
            Thread thread = new Thread(runnable, "burpai-auto-submit");
            thread.setDaemon(true);
            return thread;
        });
        this.clientSupplier = () -> new BackendClient(settings.getBackendUrl(), settings.getBackendToken());
        TaskPoller.TaskFetcher fetcher = new TaskPoller.TaskFetcher() {
            @Override
            public String getTask(String taskId) throws Exception {
                return clientSupplier.get().getTask(taskId);
            }

            @Override
            public String getAnalysis(String analysisId) throws Exception {
                return clientSupplier.get().getAnalysis(analysisId);
            }
        };
        this.poller = new TaskPoller(fetcher, new HighlightManager(api), api.logging()::logToOutput);
    }

    public void start() {
        poller.start();
    }

    public void stop() {
        poller.stop();
        executor.shutdownNow();
    }

    public ScopeRuleStore store() {
        return store;
    }

    public int sessionCount() {
        return sessionCount.get();
    }

    public void setOnCountChanged(Runnable onCountChanged) {
        this.onCountChanged = onCountChanged;
    }

    /** Called from the proxy listener for each in-scope response. */
    public void onProxyResponse(String url, String requestText, String responseText, Annotations annotations) {
        if (!store.isEnabled() || url == null || !matcher.isInScope(url)) {
            return;
        }
        PreparedHttpMessage prepared = HttpMessageFilter.prepare(requestText, responseText, url);
        if ("static_resource".equals(prepared.getBodyOmittedReason())) {
            return;
        }
        if (!rateLimiter.tryAcquire()) {
            return;
        }
        executor.submit(() -> submit(prepared, annotations));
    }

    /** Explicit, user-triggered analysis of the current Site Map (or a host subtree). */
    public int scanSiteMap(String hostFilter) {
        List<HttpRequestResponse> entries = api.siteMap().requestResponses();
        int submitted = 0;
        for (HttpRequestResponse item : entries) {
            HttpRequest request = item.request();
            if (request == null) {
                continue;
            }
            String url;
            try {
                url = request.url();
            } catch (RuntimeException ex) {
                continue;
            }
            if (url == null) {
                continue;
            }
            if (hostFilter != null && !hostFilter.trim().isEmpty() && !url.contains(hostFilter.trim())) {
                continue;
            }
            HttpResponse response = item.response();
            PreparedHttpMessage prepared = HttpMessageFilter.prepare(
                    request.toString(), response == null ? null : response.toString(), url);
            if ("static_resource".equals(prepared.getBodyOmittedReason())) {
                continue;
            }
            while (!rateLimiter.tryAcquire()) {
                try {
                    Thread.sleep(50);
                } catch (InterruptedException ex) {
                    Thread.currentThread().interrupt();
                    return submitted;
                }
            }
            final PreparedHttpMessage message = prepared;
            final Annotations annotations = item.annotations();
            executor.submit(() -> submit(message, annotations));
            submitted++;
        }
        return submitted;
    }

    private void submit(PreparedHttpMessage prepared, Annotations annotations) {
        String taskId = doSubmit(prepared);
        if (taskId != null) {
            poller.track(taskId, annotations);
            sessionCount.incrementAndGet();
            notifyCountChanged();
        }
    }

    private String doSubmit(PreparedHttpMessage prepared) {
        try {
            String json = BatchRequestBuilder.build(SOURCE, MODE, Collections.singletonList(prepared));
            String response = clientSupplier.get().submitBatch(json);
            return BackendClient.extractJsonStringField(response, "task_id");
        } catch (Exception ex) {
            api.logging().logToError("自动分析提交失败", ex);
            return null;
        }
    }

    private void notifyCountChanged() {
        Runnable callback = onCountChanged;
        if (callback != null) {
            callback.run();
        }
    }
}
