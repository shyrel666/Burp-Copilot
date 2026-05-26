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
        if (url.endsWith('/api/v1/history')) {
          return jsonResponse([]);
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

    await user.type(screen.getByLabelText(/request/i), 'GET / HTTP/1.1\r\nHost: example.test\r\n\r\n');
    await user.click(screen.getByRole('button', { name: /analyze/i }));

    expect(await screen.findByText('Checked request')).toBeInTheDocument();
    expect(screen.getByText('Calling provider')).toBeInTheDocument();
    expect(screen.getByText('Persisted')).toBeInTheDocument();
    expect(screen.getByText('Missing security header')).toBeInTheDocument();
    expect(screen.getByText('low')).toBeInTheDocument();
  });

  test('settings page never displays a submitted plain api key', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: /settings/i }));
    await screen.findByText('sk-...1234');
    await user.clear(screen.getByLabelText(/model/i));
    await user.type(screen.getByLabelText(/model/i), 'gpt-test');
    await user.type(screen.getByLabelText(/api key/i), 'sk-test-key-9999');
    await user.click(screen.getByRole('button', { name: /save provider/i }));

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

    await user.click(screen.getByRole('button', { name: /settings/i }));
    await screen.findByText('sk-...1234');
    await user.selectOptions(screen.getByLabelText(/provider/i), 'openai-compatible');
    await user.clear(screen.getByLabelText(/model/i));
    await user.type(screen.getByLabelText(/model/i), 'gpt-compat');
    await user.type(screen.getByLabelText(/base url/i), 'http://127.0.0.1:11434/v1');
    await user.type(screen.getByLabelText(/api key/i), 'sk-test-key-9999');
    await user.click(screen.getByRole('button', { name: /save provider/i }));

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
        throw new Error(`Unhandled request: ${url}`);
      }),
    );
    render(<App />);

    await user.type(
      screen.getByLabelText(/request/i),
      `POST /login HTTP/1.1\r\nHost: example.test\r\nAuthorization: Bearer ${secret}\r\n\r\npassword=${secret}`,
    );
    await user.click(screen.getByRole('button', { name: /analyze/i }));

    const failureAlert = await screen.findByRole('alert');
    expect(failureAlert).toHaveTextContent(/analysis failed/i);
    expect(failureAlert).not.toHaveTextContent(secret);
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  test('ollama provider hides api key field and shows local notice', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: /settings/i }));
    await screen.findByText('sk-...1234');
    await user.selectOptions(screen.getByLabelText(/provider/i), 'ollama');

    expect(screen.getByLabelText(/model/i)).toHaveValue('llama3');
    expect(screen.getByLabelText(/base url/i)).toHaveValue('http://localhost:11434');
    expect(screen.queryByLabelText(/api key/i)).not.toBeInTheDocument();
    expect(screen.getByText(/ollama runs locally and does not require an api key/i)).toBeInTheDocument();
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
        throw new Error(`Unhandled request: ${url}`);
      }),
    );
    render(<App />);

    await user.type(screen.getByLabelText(/request/i), 'GET / HTTP/1.1\r\nHost: example.test\r\n\r\n');
    await user.click(screen.getByRole('button', { name: /analyze/i }));

    const alerts = await screen.findAllByRole('alert');
    expect(alerts[0]).toHaveTextContent('Streaming analysis ended without a result');
    expect(screen.getByText('Streaming failed')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.queryByText('Waiting for final result')).not.toBeInTheDocument();
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

