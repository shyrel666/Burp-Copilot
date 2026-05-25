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

describe('dashboard', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
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
          });
        }
        if (url.endsWith('/api/v1/settings/provider')) {
          return jsonResponse({
            provider: 'openai',
            model: 'gpt-test',
            has_api_key: true,
            masked_api_key: 'sk-...9999',
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
});

function jsonResponse(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}
