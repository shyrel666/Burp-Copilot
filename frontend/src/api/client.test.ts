import { afterEach, expect, test, vi } from 'vitest';
import { analyzeTraffic } from './client';

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
