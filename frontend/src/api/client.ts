import type { AnalysisHistoryItem, AnalysisResponse, Mode, ProviderName, ProviderSettings, StreamStatus } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
const BACKEND_TOKEN = import.meta.env.VITE_BACKEND_TOKEN ?? '';

type AnalyzeTrafficInput = {
  mode: Mode;
  requestText: string;
  responseText?: string;
  targetUrl?: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(BACKEND_TOKEN ? { 'X-Backend-Token': BACKEND_TOKEN } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export function analyzeTraffic(input: AnalyzeTrafficInput): Promise<AnalysisResponse> {
  return request<AnalysisResponse>('/api/v1/analyze', {
    method: 'POST',
    body: JSON.stringify(analyzePayload(input)),
  });
}

export async function analyzeTrafficStream(
  input: AnalyzeTrafficInput,
  onStatus: (status: StreamStatus) => void,
): Promise<AnalysisResponse> {
  const response = await fetch(`${API_BASE}/api/v1/analyze/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(BACKEND_TOKEN ? { 'X-Backend-Token': BACKEND_TOKEN } : {}),
    },
    body: JSON.stringify(analyzePayload(input)),
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `HTTP ${response.status}`);
  }
  return readAnalysisStream(response, onStatus);
}

export function fetchHistory(): Promise<AnalysisHistoryItem[]> {
  return request<AnalysisHistoryItem[]>('/api/v1/history');
}

export function fetchSettings(): Promise<ProviderSettings> {
  return request<ProviderSettings>('/api/v1/settings');
}

export function saveProviderSettings(input: {
  provider: ProviderName;
  model: string;
  apiKey?: string;
  baseUrl?: string;
}): Promise<ProviderSettings> {
  return request<ProviderSettings>('/api/v1/settings/provider', {
    method: 'PUT',
    body: JSON.stringify({
      provider: input.provider,
      model: input.model,
      api_key: input.apiKey || null,
      base_url: input.baseUrl || null,
    }),
  });
}

function analyzePayload(input: AnalyzeTrafficInput) {
  return {
    source: 'dashboard',
    mode: input.mode,
    request_text: input.requestText,
    response_text: input.responseText || null,
    target_url: input.targetUrl || null,
    metadata: { content_encoding: 'utf-8' },
  };
}

async function readAnalysisStream(
  response: Response,
  onStatus: (status: StreamStatus) => void,
): Promise<AnalysisResponse> {
  let buffer = '';
  let result: AnalysisResponse | null = null;

  const push = (chunk: string) => {
    buffer += chunk.replace(/\r\n/g, '\n');
    let separator = buffer.indexOf('\n\n');
    while (separator >= 0) {
      handleSseBlock(buffer.slice(0, separator));
      buffer = buffer.slice(separator + 2);
      separator = buffer.indexOf('\n\n');
    }
  };

  const handleSseBlock = (block: string) => {
    const parsed = parseSseBlock(block);
    if (!parsed) return;
    if (parsed.event === 'status' && isStreamStatus(parsed.data.status)) {
      onStatus(parsed.data.status);
    }
    if (parsed.event === 'result' && isRecord(parsed.data.analysis)) {
      result = parsed.data.analysis as unknown as AnalysisResponse;
    }
  };

  if (response.body) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      push(decoder.decode(value, { stream: true }));
    }
    push(decoder.decode());
  } else {
    push(await response.text());
  }

  if (buffer.trim()) {
    handleSseBlock(buffer);
  }
  if (!result) {
    throw new Error('Streaming analysis ended without a result');
  }
  return result;
}

function parseSseBlock(block: string): { event: string; data: Record<string, unknown> } | null {
  const lines = block.split('\n');
  let event = '';
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith('event: ')) {
      event = line.slice('event: '.length);
    }
    if (line.startsWith('data: ')) {
      dataLines.push(line.slice('data: '.length));
    }
  }
  if (!event || dataLines.length === 0) return null;
  const data = JSON.parse(dataLines.join('\n')) as unknown;
  return isRecord(data) ? { event, data } : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isStreamStatus(value: unknown): value is StreamStatus {
  return value === 'redacting' || value === 'calling_provider' || value === 'parsing' || value === 'persisted' || value === 'failed';
}
