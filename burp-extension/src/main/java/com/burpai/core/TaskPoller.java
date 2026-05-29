package com.burpai.core;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

/**
 * Polls the backend every 5 seconds for the status of auto-submitted batch
 * tasks and, on completion, drives a {@link HighlightSink} to mark the matching
 * Proxy History entry.
 *
 * Dependencies are abstracted behind {@link TaskFetcher} and {@link HighlightSink}
 * so the resolution logic is unit-testable without network or Montoya runtime.
 */
public final class TaskPoller {
    public interface TaskFetcher {
        String getTask(String taskId) throws Exception;

        String getAnalysis(String analysisId) throws Exception;
    }

    public interface HighlightSink {
        /**
         * @param handle opaque target supplied to {@link #track(String, Object)};
         *               implementations know its concrete type (e.g. Montoya Annotations).
         */
        void apply(Object handle, String colorKey, String notes);
    }

    public static final class Resolution {
        public final boolean terminal;
        public final boolean highlight;
        public final String colorKey;
        public final String notes;

        Resolution(boolean terminal, boolean highlight, String colorKey, String notes) {
            this.terminal = terminal;
            this.highlight = highlight;
            this.colorKey = colorKey;
            this.notes = notes;
        }

        static Resolution pending() {
            return new Resolution(false, false, null, null);
        }
    }

    private static final long POLL_INTERVAL_SECONDS = 5;

    private final TaskFetcher fetcher;
    private final HighlightSink sink;
    private final Consumer<String> logger;
    private final Map<String, Object> pending = new ConcurrentHashMap<>();
    private ScheduledExecutorService scheduler;

    public TaskPoller(TaskFetcher fetcher, HighlightSink sink, Consumer<String> logger) {
        this.fetcher = fetcher;
        this.sink = sink;
        this.logger = logger;
    }

    public void start() {
        if (scheduler != null) {
            return;
        }
        scheduler = Executors.newSingleThreadScheduledExecutor(runnable -> {
            Thread thread = new Thread(runnable, "burpai-task-poller");
            thread.setDaemon(true);
            return thread;
        });
        scheduler.scheduleAtFixedRate(this::pollOnce, POLL_INTERVAL_SECONDS, POLL_INTERVAL_SECONDS, TimeUnit.SECONDS);
    }

    public void stop() {
        if (scheduler != null) {
            scheduler.shutdownNow();
            scheduler = null;
        }
        pending.clear();
    }

    public void track(String taskId, Object handle) {
        if (taskId != null && !taskId.isEmpty() && handle != null) {
            pending.put(taskId, handle);
        }
    }

    public int pendingCount() {
        return pending.size();
    }

    void pollOnce() {
        for (Map.Entry<String, Object> entry : pending.entrySet()) {
            String taskId = entry.getKey();
            Object handle = entry.getValue();
            try {
                Resolution resolution = resolve(fetcher.getTask(taskId), fetcher);
                if (resolution.terminal) {
                    if (resolution.highlight) {
                        sink.apply(handle, resolution.colorKey, resolution.notes);
                    }
                    pending.remove(taskId);
                }
            } catch (Exception ex) {
                if (logger != null) {
                    logger.accept("轮询任务状态失败: " + ex.getClass().getSimpleName());
                }
            }
        }
    }

    static Resolution resolve(String taskJson, TaskFetcher fetcher) throws Exception {
        String status = BackendResponseParser.taskStatus(taskJson);
        if (status == null) {
            return Resolution.pending();
        }
        switch (status) {
            case "queued":
            case "running":
                return Resolution.pending();
            case "cancelled":
                return new Resolution(true, false, null, null);
            case "done":
            case "failed":
                boolean failed = "failed".equals(status);
                String analysisId = BackendResponseParser.taskAnalysisId(taskJson);
                String analysisJson = analysisId != null ? fetcher.getAnalysis(analysisId) : null;
                List<String> severities = BackendResponseParser.severities(analysisJson);
                String colorKey = HighlightPalette.colorKeyFor(severities, failed);
                String notes = analysisJson != null
                        ? BackendResponseParser.summary(analysisJson)
                        : (failed ? "AI 分析失败，未生成结构化结果。" : "");
                return new Resolution(true, true, colorKey, notes == null ? "" : notes);
            default:
                return new Resolution(true, false, null, null);
        }
    }
}
