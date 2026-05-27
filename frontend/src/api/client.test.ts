import { afterEach, expect, test, vi } from 'vitest';
import { analyzeTraffic, submitBatch, fetchTasks, cancelTask, fetchHistory } from './client';

afterEach(() => {
  vi.unstubAllGlobals();
});

test('uses localhost backend as the default API base URL', async () => {
  const fetchMock = vi.fn(async () => {
    return new Response(
      JSON.stringify({
        analysis_id: 'analysis-1',
        summary: 'ok',
        findings: [],
        redaction_applied: true,
        llm_status: 'ok',
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    );
  });
  vi.stubGlobal('fetch', fetchMock);

  await analyzeTraffic({
    mode: 'analyze',
    requestText: 'GET / HTTP/1.1\r\nHost: example.test\r\n\r\n',
  });

  expect(fetchMock).toHaveBeenCalledWith(
    'http://127.0.0.1:8000/api/v1/analyze',
    expect.objectContaining({ method: 'POST' }),
  );
});

test('sends configured backend token header', async () => {
  vi.resetModules();
  vi.stubEnv('VITE_BACKEND_TOKEN', 'unit-dashboard-token');
  const fetchMock = vi.fn(async () => {
    return new Response(
      JSON.stringify({
        analysis_id: 'analysis-1',
        summary: 'ok',
        findings: [],
        redaction_applied: true,
        llm_status: 'ok',
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    );
  });
  vi.stubGlobal('fetch', fetchMock);
  const { analyzeTraffic: analyzeWithToken } = await import('./client');

  await analyzeWithToken({
    mode: 'analyze',
    requestText: 'GET / HTTP/1.1\r\nHost: example.test\r\n\r\n',
  });

  expect(fetchMock).toHaveBeenCalledWith(
    'http://127.0.0.1:8000/api/v1/analyze',
    expect.objectContaining({
      headers: expect.objectContaining({ 'X-Backend-Token': 'unit-dashboard-token' }),
    }),
  );
});

test('submitBatch calls batch submit endpoint with items', async () => {
  const fetchMock = vi.fn(async () => {
    return new Response(
      JSON.stringify({
        tasks: [
          { task_id: 't1', status: 'queued', created_at: '2026-05-27T12:00:00', updated_at: '2026-05-27T12:00:00', source: 'dashboard', mode: 'analyze', target_url: null, analysis_id: null, error_message: null },
        ],
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    );
  });
  vi.stubGlobal('fetch', fetchMock);

  const result = await submitBatch([{ mode: 'analyze', requestText: 'GET / HTTP/1.1\r\nHost: test\r\n\r\n' }]);
  expect(result.tasks).toHaveLength(1);
  expect(fetchMock).toHaveBeenCalledWith(
    'http://127.0.0.1:8000/api/v1/batch/submit',
    expect.objectContaining({ method: 'POST' }),
  );
});

test('fetchTasks calls batch tasks endpoint', async () => {
  const fetchMock = vi.fn(async () => {
    return new Response(JSON.stringify([]), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchMock);

  await fetchTasks();
  expect(fetchMock).toHaveBeenCalledWith(
    'http://127.0.0.1:8000/api/v1/batch/tasks',
    expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) }),
  );
});

test('fetchTasks passes status filter as query param', async () => {
  const fetchMock = vi.fn(async () => {
    return new Response(JSON.stringify([]), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchMock);

  await fetchTasks('queued');
  expect(fetchMock).toHaveBeenCalledWith(
    'http://127.0.0.1:8000/api/v1/batch/tasks?status=queued',
    expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) }),
  );
});

test('cancelTask calls cancel endpoint with POST', async () => {
  const fetchMock = vi.fn(async () => {
    return new Response(JSON.stringify({ task_id: 't1', status: 'cancelled' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchMock);

  const result = await cancelTask('t1');
  expect(result.status).toBe('cancelled');
  expect(fetchMock).toHaveBeenCalledWith(
    'http://127.0.0.1:8000/api/v1/batch/tasks/t1/cancel',
    expect.objectContaining({ method: 'POST' }),
  );
});

test('fetchHistory passes filter params as query string', async () => {
  const fetchMock = vi.fn(async () => {
    return new Response(JSON.stringify([]), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchMock);

  await fetchHistory({ mode: 'analyze', target_host: 'example.test', limit: 10 });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const calledUrl = String((fetchMock.mock.calls as any[][])[0]![0]);
  expect(calledUrl).toContain('mode=analyze');
  expect(calledUrl).toContain('target_host=example.test');
  expect(calledUrl).toContain('limit=10');
  expect(calledUrl).toContain('/api/v1/history');
});
