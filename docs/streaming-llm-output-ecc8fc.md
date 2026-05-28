# Real-time Streaming LLM Output in Burp Extension

Add real-time streaming of LLM responses to the Burp extension so users see content being generated instead of staring at a loading message, then format the final result into a readable/learnable layout.

## Phase 1: Backend — LLM Provider Streaming

**Files:** `backend/app/llm/base.py`, `openai_provider.py`, `ollama_provider.py`, `fake_provider.py`

- Add `analyze_stream(system_prompt, user_prompt) -> AsyncIterator[str]` to `BaseLLMProvider` (abstract method with default that collects `analyze()` and yields the full string)
- `OpenAIProvider`: use `stream=True` in the OpenAI API call, yield `choices[0].delta.content` chunks via httpx streaming
- `OllamaProvider`: use `stream=True` in the Ollama `/v1/chat/completions` call, yield content chunks via httpx streaming
- `FakeLLMProvider`: yield the response in small chunks with `asyncio.sleep()` to simulate streaming

## Phase 2: Backend — Content Events in AnalysisService

**Files:** `backend/app/services/analysis_service.py`, `backend/app/main.py`

- Modify `analyze_with_progress()`:
  - Replace `await self._call_provider(...)` with `async for chunk in self.provider.analyze_stream(...): yield "content", {"text": chunk}; collect full text`
  - After collecting full text, parse as before (including repair_json fallback)
  - Existing `status` and `result` events unchanged
- `_encode_sse()` already handles arbitrary event names — no change needed
- New SSE event format: `event: content\ndata: {"text":"chunk"}\n\n`

## Phase 3: Burp Extension — SSE Client

**Files:** `burp-extension/src/main/java/com/burpai/core/BackendClient.java` (new methods), new `StreamCallback.java`

- Add `StreamCallback` interface:
  ```java
  interface StreamCallback {
      void onStatus(String status);
      void onContent(String text);
      void onResult(String rawJson);
      void onError(Exception e);
  }
  ```
- Add `analyzeStream(String json, StreamCallback callback)` to `BackendClient`:
  - POST to `/api/v1/analyze/stream` with `Accept: text/event-stream`
  - Set `readTimeout` to 0 (infinite) for streaming
  - Read input stream line-by-line, parse SSE `event:` / `data:` pairs
  - Dispatch to callback based on event type
  - Handle connection errors and timeouts

## Phase 4: Burp Extension — Streaming UI

**Files:** `burp-extension/src/main/java/com/burpai/Extension.java`

- Replace `SwingWorker<String, Void>` with `SwingWorker<Void, StreamChunk>` where `StreamChunk` = `{type: status|content|result, data: String}`
- In `doInBackground()`: call `BackendClient.analyzeStream(json, callback)` where callback publishes chunks via `publish(new StreamChunk(...))`
- In `process(List<StreamChunk> chunks)`:
  - `status` → update `statusLabel` text
  - `content` → append text to `resultArea` (real-time output)
  - `result` → replace `resultArea` with `AnalysisResultFormatter.forDisplay(result)`
- `submitSelected()` switches from `/api/v1/analyze` to `/api/v1/analyze/stream`
- Cancel button: close the HTTP connection (interrupt the SwingWorker's thread)

## Phase 5: Enhanced Formatting for Learn Mode

**Files:** `burp-extension/src/main/java/com/burpai/core/AnalysisResultFormatter.java`

- Add `forLearnDisplay(String rawJson)` method with educational layout:
  - Section headers: `=== 学习笔记 ===` instead of `=== 分析结果 ===`
  - Each finding formatted as a "lesson" with `📖 概念解释`, `🔍 观察依据`, `💡 学习建议` instead of technical labels
  - Include OWASP reference links/explanations
- `submitSelected()` passes mode to formatter: use `forLearnDisplay()` when mode is "learn", `forDisplay()` when mode is "analyze"

## Phase 6: Tests

- **Backend:** Add test for `content` events in stream endpoint (extend `test_stream_analyze_emits_progress_result_and_no_raw_secrets`)
- **Backend:** Add test for `analyze_stream()` in fake provider
- **Burp extension:** Add `BackendClientStreamTest.java` for SSE parsing
- **Burp extension:** Update `AnalysisResultFormatterTest.java` for `forLearnDisplay()`

## Implementation Order

1. Phase 1 (provider streaming) — no breaking changes, default implementation falls back to non-streaming
2. Phase 2 (content events) — backward compatible, frontend ignores unknown `content` events
3. Phase 3 (SSE client) — new code, no existing code touched
4. Phase 4 (streaming UI) — modifies Extension.java, switches endpoint
5. Phase 5 (learn formatting) — additive, no breaking changes
6. Phase 6 (tests) — throughout

## Risks & Mitigations

- **SSE parsing robustness:** Use line-by-line reading with buffer for partial lines; handle `\n\n` event boundaries
- **Connection timeout during streaming:** Set `readTimeout=0` on HttpURLConnection for stream calls; add a chunk-level timeout (e.g., 60s between chunks) in the SwingWorker
- **Cancel behavior:** SwingWorker.cancel(true) interrupts the thread; BackendClient should check `Thread.interrupted()` in the read loop
- **Frontend compatibility:** Frontend already ignores unknown SSE event types; no change needed
