import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import App from './App';

const analysisResponse = {
  analysis_id: 'analysis-1',
  summary: 'Checked request',
  findings: [
    {
      title: 'Missing security header',
      severity: 'low',
      confidence: 0.5,
      evidence: '[REDACTED]',
      attack_approach: 'Review headers during authorized testing.',
      remediation: 'Set security headers.',
      owasp_category: 'A05:2021 - Security Misconfiguration',
    },
  ],
  redaction_applied: true,
  llm_status: 'ok',
};

const failedAnalysisResponse = {
  analysis_id: 'analysis-failed',
  summary: 'The LLM response could not be parsed into the required schema.',
  findings: [],
  redaction_applied: true,
  llm_status: 'failed',
};

describe('dashboard', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith('/api/v1/analyze/stream') && init?.method === 'POST') {
          return sseResponse(analysisResponse);
        }
        if (url.endsWith('/api/v1/analyze') && init?.method === 'POST') {
          return jsonResponse(analysisResponse);
        }
        if (url.includes('/api/v1/history')) {
          return jsonResponse([]);
        }
        if (url.includes('/api/v1/statistics/recent-findings')) {
          return jsonResponse([]);
        }
        if (url.includes('/api/v1/statistics/attack-surface')) {
          return jsonResponse({ total_endpoints: 0, endpoints: [] });
        }
        if (url.includes('/api/v1/statistics')) {
          return jsonResponse({
            total_analyses: 0,
            success_rate: 0,
            severity_distribution: { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
            top_vulnerability_types: [],
          });
        }
        if (url.endsWith('/api/v1/settings')) {
          return jsonResponse({
            provider: 'openai',
            model: 'gpt-4o-mini',
            has_api_key: true,
            masked_api_key: 'sk-...1234',
            base_url: null,
          });
        }
        if (url.endsWith('/api/v1/settings/provider')) {
          return jsonResponse({
            provider: 'openai',
            model: 'gpt-test',
            has_api_key: true,
            masked_api_key: 'sk-...9999',
            base_url: null,
          });
        }
        if (url.endsWith('/api/v1/batch/submit') && init?.method === 'POST') {
          return jsonResponse({
            tasks: [
              { task_id: 'task-1', status: 'queued', created_at: '2026-05-27T12:00:00', updated_at: '2026-05-27T12:00:00', source: 'dashboard', mode: 'analyze', target_url: null, analysis_id: null, error_message: null },
            ],
          });
        }
        if (url.endsWith('/api/v1/batch/tasks')) {
          return jsonResponse([]);
        }
        if (url.includes('/api/v1/batch/tasks/') && init?.method === 'POST') {
          return jsonResponse({ task_id: 'task-1', status: 'cancelled' });
        }
        throw new Error(`Unhandled request: ${url}`);
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test('submits a manual request and renders structured findings', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: /^分析$/ }));
    await user.type(screen.getByLabelText(/请求/), 'GET / HTTP/1.1\r\nHost: example.test\r\n\r\n');
    await user.click(document.querySelector('.primary-action')!);

    expect(await screen.findByText('Checked request')).toBeInTheDocument();
    expect(screen.getByText('调用提供商')).toBeInTheDocument();
    expect(screen.getByText('已保存')).toBeInTheDocument();
    expect(screen.getByText('Missing security header')).toBeInTheDocument();
    expect(screen.getByText('low')).toBeInTheDocument();
  });

  test('settings page never displays a submitted plain api key', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: /设置/ }));
    await screen.findByText('sk-...1234');
    await user.clear(screen.getByLabelText(/模型/));
    await user.type(screen.getByLabelText(/模型/), 'gpt-test');
    await user.type(screen.getByLabelText(/API 密钥/), 'sk-test-key-9999');
    await user.click(screen.getByRole('button', { name: /保存提供商/ }));

    await waitFor(() => expect(screen.getByText('sk-...9999')).toBeInTheDocument());
    expect(screen.queryByText('sk-test-key-9999')).not.toBeInTheDocument();
  });

  test('settings page saves provider, model, and base url without showing the plain api key', async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/api/v1/analyze/stream') && init?.method === 'POST') {
        return sseResponse(analysisResponse);
      }
      if (url.endsWith('/api/v1/analyze') && init?.method === 'POST') {
        return jsonResponse(analysisResponse);
      }
      if (url.endsWith('/api/v1/history')) {
        return jsonResponse([]);
      }
      if (url.includes('/api/v1/statistics')) {
        return jsonResponse({ total_analyses: 0, success_rate: 0, severity_distribution: { critical: 0, high: 0, medium: 0, low: 0, info: 0 }, top_vulnerability_types: [] });
      }
      if (url.endsWith('/api/v1/settings') && !init?.method) {
        return jsonResponse({
          provider: 'openai',
          model: 'gpt-4o-mini',
          has_api_key: true,
          masked_api_key: 'sk-...1234',
          base_url: null,
        });
      }
      if (url.endsWith('/api/v1/settings/provider')) {
        const body = JSON.parse(String(init?.body));
        expect(body).toEqual({
          provider: 'openai-compatible',
          model: 'gpt-compat',
          api_key: 'sk-test-key-9999',
          base_url: 'http://127.0.0.1:11434/v1',
        });
        return jsonResponse({
          provider: 'openai-compatible',
          model: 'gpt-compat',
          has_api_key: true,
          masked_api_key: 'sk-...9999',
          base_url: 'http://127.0.0.1:11434/v1',
        });
      }
      throw new Error(`Unhandled request: ${url}`);
    });

    vi.stubGlobal('fetch', fetchMock);
    render(<App />);

    await user.click(screen.getByRole('button', { name: /设置/ }));
    await screen.findByText('sk-...1234');
    await user.selectOptions(screen.getByLabelText(/提供商/), 'openai-compatible');
    await user.clear(screen.getByLabelText(/模型/));
    await user.type(screen.getByLabelText(/模型/), 'gpt-compat');
    await user.type(screen.getByLabelText(/基础 URL/), 'http://127.0.0.1:11434/v1');
    await user.type(screen.getByLabelText(/API 密钥/), 'sk-test-key-9999');
    await user.click(screen.getByRole('button', { name: /保存提供商/ }));

    await waitFor(() => expect(screen.getByText('sk-...9999')).toBeInTheDocument());
    expect(screen.queryByText('sk-test-key-9999')).not.toBeInTheDocument();
  });

  test('stream failure alert does not include raw request secrets', async () => {
    const user = userEvent.setup();
    const secret = 'raw-stream-secret-5555';
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith('/api/v1/analyze/stream') && init?.method === 'POST') {
          return sseResponse(failedAnalysisResponse, 'failed');
        }
        if (url.endsWith('/api/v1/history')) {
          return jsonResponse([]);
        }
        if (url.includes('/api/v1/statistics/recent-findings')) return jsonResponse([]);
        if (url.includes('/api/v1/statistics/attack-surface')) return jsonResponse({ total_endpoints: 0, endpoints: [] });
        if (url.includes('/api/v1/statistics')) {
          return jsonResponse({ total_analyses: 0, success_rate: 0, severity_distribution: { critical: 0, high: 0, medium: 0, low: 0, info: 0 }, top_vulnerability_types: [] });
        }
        return jsonResponse([]);
      }),
    );
    render(<App />);

    await user.click(screen.getByRole('button', { name: /^分析$/ }));
    await user.type(
      screen.getByLabelText(/请求/),
      `POST /login HTTP/1.1\r\nHost: example.test\r\nAuthorization: Bearer ${secret}\r\n\r\npassword=${secret}`,
    );
    await user.click(document.querySelector('.primary-action')!);

    const failureAlert = await screen.findByRole('alert');
    expect(failureAlert).toHaveTextContent(/分析失败/);
    expect(failureAlert).not.toHaveTextContent(secret);
    expect(screen.getByText('失败')).toBeInTheDocument();
  });

  test('ollama provider hides api key field and shows local notice', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: /设置/ }));
    await screen.findByText('sk-...1234');
    await user.selectOptions(screen.getByLabelText(/提供商/), 'ollama');

    expect(screen.getByLabelText(/模型/)).toHaveValue('llama3');
    expect(screen.getByLabelText(/基础 URL/)).toHaveValue('http://localhost:11434');
    expect(screen.queryByLabelText(/API 密钥/)).not.toBeInTheDocument();
    expect(screen.getByText(/Ollama 在本地运行，不需要 API 密钥/)).toBeInTheDocument();
  });

  test('batch panel submits items and shows task queue', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: /^批量$/ }));
    await user.type(screen.getByLabelText(/批量请求/), 'GET / HTTP/1.1\r\nHost: example.test\r\n\r\n');
    await user.click(screen.getByRole('button', { name: /提交批量/ }));

    expect(await screen.findByText('队列中没有任务。')).toBeInTheDocument();
  });

  test('dashboard is the default landing view and shows the compliance banner', async () => {
    render(<App />);
    expect(await screen.findByText(/仅用于已授权的安全测试/)).toBeInTheDocument();
    expect(screen.getByText(/还没有分析数据/)).toBeInTheDocument();
  });

  test('dashboard renders stat cards and attack surface when data exists', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes('/api/v1/statistics/recent-findings')) {
          return jsonResponse([
            { title: '疑似越权', severity: 'high', confidence: 0.6, owasp_category: 'A01', analysis_id: 'a1', target_url: 'https://x.test/api/users/1', created_at: '2026-05-29T10:00:00+00:00' },
          ]);
        }
        if (url.includes('/api/v1/statistics/attack-surface')) {
          return jsonResponse({
            total_endpoints: 1,
            endpoints: [
              { host: 'x.test', method: 'POST', path_template: '/admin', hit_count: 1, param_names: ['x'], has_auth_boundary: true, finding_count: 1, max_severity: 'critical', priority_score: 7.3 },
            ],
          });
        }
        if (url.includes('/api/v1/statistics')) {
          return jsonResponse({
            total_analyses: 5,
            success_rate: 0.8,
            severity_distribution: { critical: 1, high: 2, medium: 0, low: 1, info: 1 },
            top_vulnerability_types: [{ owasp_category: 'A01', count: 3 }],
          });
        }
        if (url.includes('/api/v1/history')) return jsonResponse([]);
        return jsonResponse([]);
      }),
    );
    render(<App />);

    expect(await screen.findByText('80%')).toBeInTheDocument();
    expect(screen.getByText('x.test/admin')).toBeInTheDocument();
    expect(screen.getByText('疑似越权')).toBeInTheDocument();
    expect(screen.getAllByText('5').length).toBeGreaterThanOrEqual(1);
  });

  test('history panel shows filter controls', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: /历史/ }));

    expect(screen.getByLabelText(/所有模式/)).toBeInTheDocument();
    expect(screen.getByLabelText(/任意严重性/)).toBeInTheDocument();
    expect(screen.getByText(/筛选/)).toBeInTheDocument();
    expect(screen.getByText(/清除/)).toBeInTheDocument();
  });

  test('interrupted stream marks progress failed instead of waiting for a final result', async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith('/api/v1/analyze/stream') && init?.method === 'POST') {
          return incompleteSseResponse();
        }
        if (url.endsWith('/api/v1/history')) {
          return jsonResponse([]);
        }
        if (url.includes('/api/v1/statistics/recent-findings')) return jsonResponse([]);
        if (url.includes('/api/v1/statistics/attack-surface')) return jsonResponse({ total_endpoints: 0, endpoints: [] });
        if (url.includes('/api/v1/statistics')) {
          return jsonResponse({ total_analyses: 0, success_rate: 0, severity_distribution: { critical: 0, high: 0, medium: 0, low: 0, info: 0 }, top_vulnerability_types: [] });
        }
        return jsonResponse([]);
      }),
    );
    render(<App />);

    await user.click(screen.getByRole('button', { name: /^分析$/ }));
    await user.type(screen.getByLabelText(/请求/), 'GET / HTTP/1.1\r\nHost: example.test\r\n\r\n');
    await user.click(document.querySelector('.primary-action')!);

    const alerts = await screen.findAllByRole('alert');
    expect(alerts[0]).toHaveTextContent(/Streaming analysis ended without a result/);
    expect(screen.getByText('流式传输失败')).toBeInTheDocument();
    expect(screen.getByText('失败')).toBeInTheDocument();
    expect(screen.queryByText('等待最终结果')).not.toBeInTheDocument();
  });


});

function jsonResponse(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

function sseResponse(analysis: unknown, finalStatus = 'persisted'): Response {
  const body = [
    'event: status',
    'data: {"status":"redacting"}',
    '',
    'event: status',
    'data: {"status":"calling_provider"}',
    '',
    'event: content',
    'data: {"text":"chunk1"}',
    '',
    'event: content',
    'data: {"text":"chunk2"}',
    '',
    'event: status',
    'data: {"status":"parsing"}',
    '',
    'event: status',
    `data: ${JSON.stringify({ status: finalStatus })}`,
    '',
    'event: result',
    `data: ${JSON.stringify({ analysis })}`,
    '',
    '',
  ].join('\n');
  return new Response(body, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  });
}

function incompleteSseResponse(): Response {
  const body = [
    'event: status',
    'data: {"status":"redacting"}',
    '',
    'event: status',
    'data: {"status":"calling_provider"}',
    '',
    '',
  ].join('\n');
  return new Response(body, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  });
}
