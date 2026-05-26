import { AlertCircle, BookOpen, History, KeyRound, Play, ShieldCheck } from 'lucide-react';
import { FormEvent, useEffect, useState } from 'react';
import { analyzeTrafficStream, fetchHistory, fetchSettings, saveProviderSettings } from './api/client';
import type { AnalysisHistoryItem, AnalysisResponse, Finding, Mode, ProviderSettings, StreamStatus } from './types';

type View = 'analyze' | 'history' | 'settings';

const emptySettings: ProviderSettings = {
  provider: 'openai',
  model: 'gpt-4o-mini',
  has_api_key: false,
  masked_api_key: null,
  base_url: null,
};

export default function App() {
  const [view, setView] = useState<View>('analyze');
  const [mode, setMode] = useState<Mode>('analyze');
  const [targetUrl, setTargetUrl] = useState('');
  const [requestText, setRequestText] = useState('');
  const [responseText, setResponseText] = useState('');
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [streamStatuses, setStreamStatuses] = useState<StreamStatus[]>([]);
  const [history, setHistory] = useState<AnalysisHistoryItem[]>([]);
  const [settings, setSettings] = useState<ProviderSettings>(emptySettings);
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadHistory();
  }, []);

  useEffect(() => {
    if (view === 'settings') {
      void loadSettings();
    }
  }, [view]);

  async function loadHistory() {
    try {
      setHistory(await fetchHistory());
    } catch {
      setHistory([]);
    }
  }

  async function loadSettings() {
    try {
      setSettings(await fetchSettings());
    } catch (exc) {
      setError(errorMessage(exc));
    }
  }

  async function submitAnalysis(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setAnalysis(null);
    setStreamStatuses([]);
    try {
      const result = await analyzeTrafficStream(
        {
          mode,
          requestText,
          responseText,
          targetUrl,
        },
        (status) => setStreamStatuses((statuses) => [...statuses, status]),
      );
      setAnalysis(result);
      await loadHistory();
    } catch (exc) {
      setStreamStatuses((statuses) => [...statuses, 'failed']);
      setError(errorMessage(exc));
    } finally {
      setLoading(false);
    }
  }

  async function submitSettings(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await saveProviderSettings({
        provider: settings.provider,
        model: settings.model,
        apiKey,
        baseUrl: settings.base_url || undefined,
      });
      setSettings(result);
      setApiKey('');
    } catch (exc) {
      setError(errorMessage(exc));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck aria-hidden="true" />
          <div>
            <strong>Burp AI</strong>
            <span>HTTP Analyzer</span>
          </div>
        </div>
        <button className={view === 'history' ? 'nav-active' : ''} onClick={() => setView('history')}>
          <History aria-hidden="true" />
          History
        </button>
        <button className={view === 'settings' ? 'nav-active' : ''} onClick={() => setView('settings')}>
          <KeyRound aria-hidden="true" />
          Settings
        </button>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <h1>{viewTitle(view)}</h1>
            <p>Local-first analysis for authorized HTTP security review.</p>
          </div>
          <div className="status-pill">Redaction required</div>
        </header>

        {error ? (
          <div className="notice" role="alert">
            <AlertCircle aria-hidden="true" />
            {error}
          </div>
        ) : null}

        {view === 'analyze' ? (
          <section className="tool-grid">
            <form className="analysis-form" onSubmit={submitAnalysis}>
              <div className="segmented" aria-label="Analysis mode">
                <button
                  type="button"
                  aria-label="Use security review mode"
                  className={mode === 'analyze' ? 'selected' : ''}
                  onClick={() => setMode('analyze')}
                >
                  <ShieldCheck aria-hidden="true" />
                  Analyze
                </button>
                <button
                  type="button"
                  aria-label="Use learning mode"
                  className={mode === 'learn' ? 'selected' : ''}
                  onClick={() => setMode('learn')}
                >
                  <BookOpen aria-hidden="true" />
                  Learn
                </button>
              </div>

              <label>
                Target URL
                <input value={targetUrl} onChange={(event) => setTargetUrl(event.target.value)} placeholder="https://example.test/path" />
              </label>

              <label>
                Request
                <textarea
                  value={requestText}
                  onChange={(event) => setRequestText(event.target.value)}
                  placeholder={'GET / HTTP/1.1\r\nHost: example.test\r\n\r\n'}
                  required
                />
              </label>

              <label>
                Response
                <textarea
                  value={responseText}
                  onChange={(event) => setResponseText(event.target.value)}
                  placeholder={'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n'}
                />
              </label>

              <button className="primary-action" disabled={loading || !requestText.trim()}>
                <Play aria-hidden="true" />
                {loading ? 'Analyzing...' : 'Analyze'}
              </button>
            </form>
            <AnalysisResult analysis={analysis} streamStatuses={streamStatuses} />
          </section>
        ) : null}

        {view === 'history' ? <HistoryPanel items={history} /> : null}
        {view === 'settings' ? (
          <SettingsPanel
            settings={settings}
            setSettings={setSettings}
            apiKey={apiKey}
            setApiKey={setApiKey}
            loading={loading}
            onSubmit={submitSettings}
          />
        ) : null}
      </main>
    </div>
  );
}

function AnalysisResult({ analysis, streamStatuses }: { analysis: AnalysisResponse | null; streamStatuses: StreamStatus[] }) {
  const streamFailed = streamStatuses.includes('failed');
  if (!analysis) {
    return (
      <section className={streamStatuses.length ? 'result-panel' : 'result-panel empty-state'}>
        {streamStatuses.length ? (
          <>
            <div className="result-header">
              <div>
                <h2>{streamFailed ? 'Streaming failed' : 'Streaming analysis'}</h2>
                <span>{streamFailed ? 'Analysis did not complete' : 'Waiting for final result'}</span>
              </div>
            </div>
            <ProgressList statuses={streamStatuses} />
            {streamFailed ? (
              <div className="notice result-error" role="alert">
                <AlertCircle aria-hidden="true" />
                Stream ended without a result. The analysis could not be completed.
              </div>
            ) : null}
          </>
        ) : (
          <>
            <ShieldCheck aria-hidden="true" />
            <p>Submit a request to view redacted findings.</p>
          </>
        )}
      </section>
    );
  }
  return (
    <section className="result-panel">
      <div className="result-header">
        <div>
          <h2>{analysis.summary}</h2>
          <span>LLM status: {analysis.llm_status}</span>
        </div>
        <span className="status-pill">{analysis.redaction_applied ? 'Redacted' : 'Not redacted'}</span>
      </div>
      {analysis.llm_status === 'failed' ? (
        <div className="notice result-error" role="alert">
          <AlertCircle aria-hidden="true" />
          Analysis failed. The provider response could not be converted into structured findings.
        </div>
      ) : null}
      <ProgressList statuses={streamStatuses} />
      <div className="findings-list">
        {analysis.findings.map((finding) => (
          <FindingCard key={`${finding.title}-${finding.evidence}`} finding={finding} />
        ))}
      </div>
    </section>
  );
}

function ProgressList({ statuses }: { statuses: StreamStatus[] }) {
  if (statuses.length === 0) return null;
  return (
    <ol className="progress-list" aria-label="Analysis progress">
      {statuses.map((status, index) => (
        <li key={`${status}-${index}`}>{streamStatusLabel(status)}</li>
      ))}
    </ol>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  return (
    <article className="finding-card">
      <div className="finding-title">
        <h3>{finding.title}</h3>
        <span className={`severity severity-${finding.severity}`}>{finding.severity}</span>
      </div>
      <p>{finding.evidence}</p>
      <dl>
        <dt>Approach</dt>
        <dd>{finding.attack_approach}</dd>
        <dt>Remediation</dt>
        <dd>{finding.remediation}</dd>
        {finding.owasp_category ? (
          <>
            <dt>OWASP</dt>
            <dd>{finding.owasp_category}</dd>
          </>
        ) : null}
      </dl>
    </article>
  );
}

function HistoryPanel({ items }: { items: AnalysisHistoryItem[] }) {
  return (
    <section className="list-panel">
      {items.length === 0 ? (
        <p className="muted">No analysis history yet.</p>
      ) : (
        items.map((item) => (
          <article className="history-row" key={item.analysis_id}>
            <div>
              <strong>{item.summary}</strong>
              <span>{item.target_url || item.mode}</span>
            </div>
            <span className="status-pill">{item.llm_status}</span>
          </article>
        ))
      )}
    </section>
  );
}

function SettingsPanel({
  settings,
  setSettings,
  apiKey,
  setApiKey,
  loading,
  onSubmit,
}: {
  settings: ProviderSettings;
  setSettings: (settings: ProviderSettings) => void;
  apiKey: string;
  setApiKey: (value: string) => void;
  loading: boolean;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <form className="settings-form" onSubmit={onSubmit}>
      <label>
        Provider
        <select
          value={settings.provider}
          onChange={(event) =>
            setSettings({
              ...settings,
              provider: event.target.value as ProviderSettings['provider'],
            })
          }
        >
          <option value="openai">openai</option>
          <option value="openai-compatible">openai-compatible</option>
        </select>
      </label>
      <label>
        Model
        <input value={settings.model} onChange={(event) => setSettings({ ...settings, model: event.target.value })} />
      </label>
      <label>
        Base URL
        <input
          value={settings.base_url ?? ''}
          onChange={(event) => setSettings({ ...settings, base_url: event.target.value || null })}
          placeholder="http://127.0.0.1:11434/v1"
        />
      </label>
      <label>
        API key
        <input
          type="password"
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
          placeholder={settings.has_api_key ? 'Leave blank to keep current key' : 'Paste provider key'}
        />
      </label>
      <div className="key-state">
        <span>Configured key</span>
        <strong>{settings.masked_api_key || 'Not configured'}</strong>
      </div>
      <button className="primary-action" disabled={loading}>
        <KeyRound aria-hidden="true" />
        Save Provider
      </button>
    </form>
  );
}

function viewTitle(view: View) {
  if (view === 'history') return 'Analysis history';
  if (view === 'settings') return 'Provider settings';
  return 'Manual analysis';
}

function streamStatusLabel(status: StreamStatus) {
  if (status === 'calling_provider') return 'Calling provider';
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Unexpected error';
}
