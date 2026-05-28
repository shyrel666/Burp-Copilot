import { AlertCircle, BookOpen, Globe, History, KeyRound, Layers, Play, ShieldCheck, X } from 'lucide-react';
import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { analyzeTrafficStream, cancelTask, fetchHistory, fetchSettings, fetchTasks, saveProviderSettings, submitBatch } from './api/client';
import { LocaleContext, getMessages, useLocale, type Locale, type LocaleKeys } from './i18n';
import type { AnalysisHistoryItem, AnalysisResponse, Finding, HistoryFilters, Mode, ProviderName, ProviderSettings, StreamStatus, TaskInfo } from './types';

type View = 'analyze' | 'batch' | 'history' | 'settings';

const emptySettings: ProviderSettings = {
  provider: 'openai',
  model: 'gpt-4o-mini',
  has_api_key: false,
  masked_api_key: null,
  base_url: null,
};

function defaultModelForProvider(provider: ProviderName): string {
  if (provider === 'ollama') return 'llama3';
  if (provider === 'deepseek') return 'deepseek-v4-pro';
  return 'gpt-4o-mini';
}

function defaultBaseUrlForProvider(provider: ProviderName): string | null {
  if (provider === 'ollama') return 'http://localhost:11434';
  if (provider === 'deepseek') return null;
  return null;
}

const LOCALE_STORAGE_KEY = 'burp-ai-locale';

function getInitialLocale(): Locale {
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY);
  if (stored === 'en' || stored === 'zh') return stored;
  return 'zh';
}

export default function App() {
  const [locale, setLocaleState] = useState<Locale>(getInitialLocale);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    localStorage.setItem(LOCALE_STORAGE_KEY, l);
  }, []);

  const t = useCallback((key: LocaleKeys) => getMessages(locale)[key], [locale]);

  const localeCtx = useMemo(() => ({ locale, setLocale, t }), [locale, setLocale, t]);

  return (
    <LocaleContext.Provider value={localeCtx}>
      <AppInner />
    </LocaleContext.Provider>
  );
}

function AppInner() {
  const { t, locale, setLocale } = useLocale();

  function localizedErrorMessage(err: unknown) {
    return err instanceof Error ? err.message : t('error_unexpected');
  }

  const [view, setView] = useState<View>('analyze');
  const [mode, setMode] = useState<Mode>('analyze');
  const [targetUrl, setTargetUrl] = useState('');
  const [requestText, setRequestText] = useState('');
  const [responseText, setResponseText] = useState('');
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [streamStatuses, setStreamStatuses] = useState<StreamStatus[]>([]);
  const [streamingText, setStreamingText] = useState('');
  const [history, setHistory] = useState<AnalysisHistoryItem[]>([]);
  const [settings, setSettings] = useState<ProviderSettings>(emptySettings);
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [historyFilters, setHistoryFilters] = useState<HistoryFilters>({});

  useEffect(() => {
    void loadHistory();
  }, []);

  useEffect(() => {
    if (view === 'settings') {
      void loadSettings();
    }
  }, [view]);

  const loadHistory = useCallback(async (filters?: HistoryFilters) => {
    try {
      setHistory(await fetchHistory(filters));
    } catch {
      setHistory([]);
    }
  }, []);

  async function loadTasks() {
    try {
      setTasks(await fetchTasks());
    } catch {
      setTasks([]);
    }
  }

  useEffect(() => {
    if (view !== 'batch') return;
    const interval = setInterval(() => void loadTasks(), 3000);
    return () => clearInterval(interval);
  }, [view]);

  async function loadSettings() {
    try {
      setSettings(await fetchSettings());
    } catch (exc) {
      setError(localizedErrorMessage(exc));
    }
  }

  async function submitAnalysis(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setAnalysis(null);
    setStreamStatuses([]);
    setStreamingText('');
    try {
      const result = await analyzeTrafficStream(
        { mode, requestText, responseText, targetUrl },
        (status) => setStreamStatuses((statuses) => [...statuses, status]),
        (text) => setStreamingText((prev) => prev + text),
      );
      setAnalysis(result);
      setStreamingText('');
      await loadHistory();
    } catch (exc) {
      setStreamStatuses((statuses) => [...statuses, 'failed']);
      setError(localizedErrorMessage(exc));
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
      setError(localizedErrorMessage(exc));
    } finally {
      setLoading(false);
    }
  }

  const viewTitleMap: Record<View, LocaleKeys> = {
    analyze: 'view_analyze',
    batch: 'view_batch',
    history: 'view_history',
    settings: 'view_settings',
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck aria-hidden="true" />
          <div>
            <strong>{t('brand_name')}</strong>
            <span>{t('brand_sub')}</span>
          </div>
        </div>
        <button aria-label={t('nav_analyze')} className={view === 'analyze' ? 'nav-active' : ''} onClick={() => setView('analyze')}>
          <Play aria-hidden="true" />
          {t('nav_analyze')}
        </button>
        <button className={view === 'batch' ? 'nav-active' : ''} onClick={() => { setView('batch'); void loadTasks(); }}>
          <Layers aria-hidden="true" />
          {t('nav_batch')}
        </button>
        <button className={view === 'history' ? 'nav-active' : ''} onClick={() => { setView('history'); void loadHistory(historyFilters); }}>
          <History aria-hidden="true" />
          {t('nav_history')}
        </button>
        <button className={view === 'settings' ? 'nav-active' : ''} onClick={() => setView('settings')}>
          <KeyRound aria-hidden="true" />
          {t('nav_settings')}
        </button>

        <div style={{ marginTop: 'auto' }}>
          <button
            aria-label={t('lang_switch_label')}
            onClick={() => setLocale(locale === 'zh' ? 'en' : 'zh')}
          >
            <Globe aria-hidden="true" />
            {locale === 'zh' ? 'EN' : '中文'}
          </button>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <h1>{t(viewTitleMap[view])}</h1>
            <p>{t('subtitle')}</p>
          </div>
          <div className="status-pill">{t('status_redaction')}</div>
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
                  aria-label={t('mode_analyze')}
                  className={mode === 'analyze' ? 'selected' : ''}
                  onClick={() => setMode('analyze')}
                >
                  <ShieldCheck aria-hidden="true" />
                  {t('mode_analyze')}
                </button>
                <button
                  type="button"
                  aria-label={t('mode_learn')}
                  className={mode === 'learn' ? 'selected' : ''}
                  onClick={() => setMode('learn')}
                >
                  <BookOpen aria-hidden="true" />
                  {t('mode_learn')}
                </button>
              </div>

              <label>
                {t('label_target_url')}
                <input value={targetUrl} onChange={(e) => setTargetUrl(e.target.value)} placeholder={t('placeholder_target_url')} />
              </label>

              <label>
                {t('label_request')}
                <textarea
                  value={requestText}
                  onChange={(e) => setRequestText(e.target.value)}
                  placeholder={t('placeholder_request')}
                  required
                />
              </label>

              <label>
                {t('label_response')}
                <textarea
                  value={responseText}
                  onChange={(e) => setResponseText(e.target.value)}
                  placeholder={t('placeholder_response')}
                />
              </label>

              <button className="primary-action" disabled={loading || !requestText.trim()}>
                <Play aria-hidden="true" />
                {loading ? t('btn_analyzing') : t('btn_analyze')}
              </button>
            </form>
            <AnalysisResult analysis={analysis} streamStatuses={streamStatuses} streamingText={streamingText} />
          </section>
        ) : null}

        {view === 'batch' ? (
          <BatchPanel tasks={tasks} onRefresh={loadTasks} setError={setError} />
        ) : null}
        {view === 'history' ? (
          <HistoryPanel
            items={history}
            filters={historyFilters}
            setFilters={setHistoryFilters}
            onApplyFilters={(f) => loadHistory(f)}
          />
        ) : null}
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

function AnalysisResult({ analysis, streamStatuses, streamingText }: { analysis: AnalysisResponse | null; streamStatuses: StreamStatus[]; streamingText: string }) {
  const { t } = useLocale();
  const streamFailed = streamStatuses.includes('failed');
  if (!analysis) {
    return (
      <section className={streamStatuses.length ? 'result-panel' : 'result-panel empty-state'}>
        {streamStatuses.length ? (
          <>
            <div className="result-header">
              <div>
                <h2>{streamFailed ? t('result_stream_failed') : t('result_streaming')}</h2>
                <span>{streamFailed ? t('result_not_complete') : t('result_waiting')}</span>
              </div>
            </div>
            <ProgressList statuses={streamStatuses} />
            {streamingText ? (
              <pre className="streaming-text">{streamingText}</pre>
            ) : null}
            {streamFailed ? (
              <div className="notice result-error" role="alert">
                <AlertCircle aria-hidden="true" />
                {t('result_stream_error')}
              </div>
            ) : null}
          </>
        ) : (
          <>
            <ShieldCheck aria-hidden="true" />
            <p>{t('empty_state')}</p>
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
          <span>{t('result_llm_status')}: {analysis.llm_status}</span>
        </div>
        <span className="status-pill">{analysis.redaction_applied ? t('result_redacted') : t('result_not_redacted')}</span>
      </div>
      {analysis.llm_status === 'failed' ? (
        <div className="notice result-error" role="alert">
          <AlertCircle aria-hidden="true" />
          {t('result_failed_notice')}
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
  const { t } = useLocale();
  if (statuses.length === 0) return null;

  const statusLabelMap: Record<string, LocaleKeys> = {
    redacting: 'stream_redacting',
    calling_provider: 'stream_calling_provider',
    parsing: 'stream_parsing',
    persisted: 'stream_persisted',
    failed: 'stream_failed',
  };

  return (
    <ol className="progress-list" aria-label="Analysis progress">
      {statuses.map((status, index) => (
        <li key={`${status}-${index}`}>
          {statusLabelMap[status] ? t(statusLabelMap[status]) : status}
        </li>
      ))}
    </ol>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  const { t } = useLocale();
  return (
    <article className="finding-card">
      <div className="finding-title">
        <h3>{finding.title}</h3>
        <span className={`severity severity-${finding.severity}`}>{finding.severity}</span>
      </div>
      <p>{finding.evidence}</p>
      <dl>
        <dt>{t('finding_approach')}</dt>
        <dd>{finding.attack_approach}</dd>
        <dt>{t('finding_remediation')}</dt>
        <dd>{finding.remediation}</dd>
        {finding.owasp_category ? (
          <>
            <dt>{t('finding_owasp')}</dt>
            <dd>{finding.owasp_category}</dd>
          </>
        ) : null}
      </dl>
    </article>
  );
}

function BatchPanel({
  tasks,
  onRefresh,
  setError,
}: {
  tasks: TaskInfo[];
  onRefresh: () => void;
  setError: (msg: string | null) => void;
}) {
  const { t } = useLocale();
  const [batchText, setBatchText] = useState('');
  const [batchMode, setBatchMode] = useState<Mode>('analyze');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const lines = batchText.split('\n---\n').filter((s) => s.trim());
    if (lines.length === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitBatch(
        lines.map((text) => ({ mode: batchMode, requestText: text.trim() })),
      );
      setBatchText('');
      onRefresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : t('error_batch_failed'));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancel(taskId: string) {
    try {
      await cancelTask(taskId);
      onRefresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : t('error_cancel_failed'));
    }
  }

  return (
    <section className="list-panel">
      <form className="analysis-form" onSubmit={handleSubmit}>
        <div className="segmented" aria-label={t('batch_mode_label')}>
          <button type="button" className={batchMode === 'analyze' ? 'selected' : ''} onClick={() => setBatchMode('analyze')}>
            <ShieldCheck aria-hidden="true" /> {t('mode_analyze')}
          </button>
          <button type="button" className={batchMode === 'learn' ? 'selected' : ''} onClick={() => setBatchMode('learn')}>
            <BookOpen aria-hidden="true" /> {t('mode_learn')}
          </button>
        </div>
        <label>
          {t('batch_textarea_label')}
          <textarea
            value={batchText}
            onChange={(e) => setBatchText(e.target.value)}
            placeholder={t('batch_placeholder')}
            rows={8}
          />
        </label>
        <button className="primary-action" disabled={submitting || !batchText.trim()}>
          <Layers aria-hidden="true" />
          {submitting ? t('btn_submitting') : t('btn_submit_batch')}
        </button>
      </form>

      <h3 style={{ marginTop: '1.5rem' }}>{t('task_queue')}</h3>
      <button type="button" className="secondary-action" onClick={onRefresh} style={{ marginBottom: '0.75rem' }}>
        {t('btn_refresh')}
      </button>
      {tasks.length === 0 ? (
        <p className="muted">{t('no_tasks')}</p>
      ) : (
        tasks.map((task) => (
          <article className="history-row" key={task.task_id}>
            <div>
              <strong>{task.mode} — {task.target_url || task.task_id.slice(0, 8)}</strong>
              <span className={`status-pill status-${task.status}`}>{task.status}</span>
              {task.error_message ? <span className="muted"> {task.error_message}</span> : null}
            </div>
            {(task.status === 'queued' || task.status === 'running') ? (
              <button type="button" title="Cancel" onClick={() => handleCancel(task.task_id)}>
                <X aria-hidden="true" size={14} />
              </button>
            ) : null}
          </article>
        ))
      )}
    </section>
  );
}

function HistoryPanel({
  items,
  filters,
  setFilters,
  onApplyFilters,
}: {
  items: AnalysisHistoryItem[];
  filters: HistoryFilters;
  setFilters: (f: HistoryFilters) => void;
  onApplyFilters: (f: HistoryFilters) => void;
}) {
  const { t } = useLocale();
  const [selectedItem, setSelectedItem] = useState<AnalysisHistoryItem | null>(null);

  return (
    <section className="list-panel">
      <div className="filter-bar">
        <select
          aria-label={t('filter_all_modes')}
          value={filters.mode || ''}
          onChange={(e) => setFilters({ ...filters, mode: (e.target.value || undefined) as Mode | undefined })}
        >
          <option value="">{t('filter_all_modes')}</option>
          <option value="analyze">{t('mode_analyze')}</option>
          <option value="learn">{t('mode_learn')}</option>
        </select>
        <select
          aria-label={t('filter_any_severity')}
          value={filters.min_severity || ''}
          onChange={(e) => setFilters({ ...filters, min_severity: (e.target.value || undefined) as HistoryFilters['min_severity'] })}
        >
          <option value="">{t('filter_any_severity')}</option>
          <option value="critical">{t('filter_critical')}</option>
          <option value="high">{t('filter_high')}</option>
          <option value="medium">{t('filter_medium')}</option>
          <option value="low">{t('filter_low')}</option>
        </select>
        <input
          placeholder={t('placeholder_target_host')}
          value={filters.target_host || ''}
          onChange={(e) => setFilters({ ...filters, target_host: e.target.value || undefined })}
        />
        <button type="button" onClick={() => onApplyFilters(filters)}>{t('btn_filter')}</button>
        <button type="button" onClick={() => { const empty = {}; setFilters(empty); onApplyFilters(empty); }}>{t('btn_clear')}</button>
      </div>
      {items.length === 0 ? (
        <p className="muted">{t('no_history')}</p>
      ) : (
        items.map((item) => (
          <article
            className="history-row history-row-clickable"
            key={item.analysis_id}
            onClick={() => setSelectedItem(item)}
          >
            <div>
              <strong>{item.summary}</strong>
              <span>{item.target_url || item.mode}</span>
            </div>
            <span className="status-pill">{item.llm_status}</span>
          </article>
        ))
      )}
      {selectedItem ? (
        <HistoryDetailModal item={selectedItem} onClose={() => setSelectedItem(null)} />
      ) : null}
    </section>
  );
}

function HistoryDetailModal({ item, onClose }: { item: AnalysisHistoryItem; onClose: () => void }) {
  const { t } = useLocale();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h2>{item.summary}</h2>
            <span className="muted">{item.target_url || item.mode} · {item.created_at}</span>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">
          {item.findings.length === 0 ? (
            <p className="muted">{t('no_findings')}</p>
          ) : (
            <div className="findings-list">
              {item.findings.map((finding) => (
                <FindingCard key={`${finding.title}-${finding.evidence}`} finding={finding} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
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
  const { t } = useLocale();
  return (
    <form className="settings-form" onSubmit={onSubmit}>
      <label>
        {t('label_provider')}
        <select
          value={settings.provider}
          onChange={(event) => {
            const newProvider = event.target.value as ProviderSettings['provider'];
            setSettings({
              ...settings,
              provider: newProvider,
              model: defaultModelForProvider(newProvider),
              base_url: defaultBaseUrlForProvider(newProvider),
            });
            setApiKey('');
          }}
        >
          <option value="openai">openai</option>
          <option value="openai-compatible">openai-compatible</option>
          <option value="deepseek">deepseek</option>
          <option value="ollama">ollama</option>
        </select>
      </label>
      <label>
        {t('label_model')}
        <input value={settings.model} onChange={(event) => setSettings({ ...settings, model: event.target.value })} />
      </label>
      {settings.provider !== 'deepseek' ? (
        <label>
          {t('label_base_url')}
          <input
            value={settings.base_url ?? ''}
            onChange={(event) => setSettings({ ...settings, base_url: event.target.value || null })}
            placeholder={t('placeholder_base_url')}
          />
        </label>
      ) : null}
      {settings.provider !== 'ollama' ? (
        <label>
          {t('label_api_key')}
          <input
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder={settings.has_api_key ? t('placeholder_api_key_keep') : t('placeholder_api_key_paste')}
          />
        </label>
      ) : null}
      {settings.provider !== 'ollama' ? (
        <div className="key-state">
          <span>{t('configured_key')}</span>
          <strong>{settings.masked_api_key || t('not_configured')}</strong>
        </div>
      ) : null}
      {settings.provider === 'ollama' ? (
        <p className="muted">{t('ollama_note')}</p>
      ) : null}
      <button className="primary-action" disabled={loading}>
        <KeyRound aria-hidden="true" />
        {t('btn_save_provider')}
      </button>
    </form>
  );
}

