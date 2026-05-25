import type { AnalysisHistoryItem, AnalysisResponse, Mode, ProviderSettings } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export function analyzeTraffic(input: {
  mode: Mode;
  requestText: string;
  responseText?: string;
  targetUrl?: string;
}): Promise<AnalysisResponse> {
  return request<AnalysisResponse>('/api/v1/analyze', {
    method: 'POST',
    body: JSON.stringify({
      source: 'dashboard',
      mode: input.mode,
      request_text: input.requestText,
      response_text: input.responseText || null,
      target_url: input.targetUrl || null,
      metadata: { content_encoding: 'utf-8' },
    }),
  });
}

export function fetchHistory(): Promise<AnalysisHistoryItem[]> {
  return request<AnalysisHistoryItem[]>('/api/v1/history');
}

export function fetchSettings(): Promise<ProviderSettings> {
  return request<ProviderSettings>('/api/v1/settings');
}

export function saveProviderSettings(input: {
  provider: string;
  model: string;
  apiKey?: string;
}): Promise<ProviderSettings> {
  return request<ProviderSettings>('/api/v1/settings/provider', {
    method: 'PUT',
    body: JSON.stringify({
      provider: input.provider,
      model: input.model,
      api_key: input.apiKey || null,
    }),
  });
}
