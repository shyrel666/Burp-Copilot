import { AlertCircle, Compass, ShieldAlert, Sparkles } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  fetchArchitecture,
  fetchAttackSurface,
  fetchRecentFindings,
  fetchRoadmap,
  fetchStatistics,
} from './api/client';
import { useLocale, type LocaleKeys } from './i18n';
import type {
  ArchitectureProfile,
  AttackSurfaceResponse,
  RecentFinding,
  RoadmapResponse,
  Severity,
  StatisticsResponse,
} from './types';

const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low', 'info'];
const SEVERITY_COLORS: Record<Severity, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
  info: '#64748b',
};

export function Dashboard({ onSelectAnalysis }: { onSelectAnalysis: (id: string) => void }) {
  const { t } = useLocale();
  const [stats, setStats] = useState<StatisticsResponse | null>(null);
  const [recent, setRecent] = useState<RecentFinding[]>([]);
  const [surface, setSurface] = useState<AttackSurfaceResponse | null>(null);

  const load = useCallback(async () => {
    const [s, r, a] = await Promise.allSettled([
      fetchStatistics(),
      fetchRecentFindings(20),
      fetchAttackSurface(undefined, 50),
    ]);
    if (s.status === 'fulfilled') setStats(s.value);
    if (r.status === 'fulfilled' && Array.isArray(r.value)) setRecent(r.value);
    if (a.status === 'fulfilled' && Array.isArray(a.value?.endpoints)) setSurface(a.value);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const hosts = useMemo(() => {
    const set = new Set<string>();
    (surface?.endpoints ?? []).forEach((e) => {
      if (e.host) set.add(e.host);
    });
    return [...set];
  }, [surface]);

  if (stats && stats.total_analyses === 0) {
    return (
      <section className="dashboard">
        <ComplianceBanner />
        <div className="result-panel empty-state">
          <Sparkles aria-hidden="true" />
          <h2>{t('dashboard_empty_title')}</h2>
          <p>{t('dashboard_empty_hint')}</p>
        </div>
      </section>
    );
  }

  return (
    <section className="dashboard">
      <ComplianceBanner />
      <div className="stat-cards">
        <StatCard label={t('dashboard_total')} value={stats ? String(stats.total_analyses) : '—'} />
        <StatCard
          label={t('dashboard_success_rate')}
          value={stats ? `${Math.round(stats.success_rate * 100)}%` : '—'}
        />
        <StatCard
          label={t('dashboard_top_vuln')}
          value={stats?.top_vulnerability_types[0]?.owasp_category ?? t('dashboard_none')}
        />
      </div>

      <div className="dashboard-grid">
        <div className="dashboard-col">
          {stats ? <SeverityDonut stats={stats} /> : null}
          {surface ? <AttackSurfacePanel surface={surface} /> : null}
        </div>
        <div className="dashboard-col">
          <ArchitecturePanel hosts={hosts} />
          <RecentTimeline findings={recent} onSelectAnalysis={onSelectAnalysis} />
        </div>
      </div>
    </section>
  );
}

function ComplianceBanner() {
  const { t } = useLocale();
  return (
    <div className="compliance-banner">
      <ShieldAlert aria-hidden="true" size={16} />
      <span>{t('compliance_banner')}</span>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="stat-card">
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
    </article>
  );
}

function SeverityDonut({ stats }: { stats: StatisticsResponse }) {
  const { t } = useLocale();
  const dist = stats.severity_distribution;
  const total = SEVERITY_ORDER.reduce((sum, sev) => sum + dist[sev], 0);
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <article className="panel-card">
      <h3>{t('dashboard_severity_chart')}</h3>
      <div className="donut-wrap">
        <svg viewBox="0 0 160 160" className="donut" role="img" aria-label={t('dashboard_severity_chart')}>
          <circle cx="80" cy="80" r={radius} className="donut-track" fill="none" strokeWidth="20" />
          {total > 0
            ? SEVERITY_ORDER.map((sev) => {
                const value = dist[sev];
                if (value === 0) return null;
                const length = (value / total) * circumference;
                const segment = (
                  <circle
                    key={sev}
                    cx="80"
                    cy="80"
                    r={radius}
                    fill="none"
                    stroke={SEVERITY_COLORS[sev]}
                    strokeWidth="20"
                    strokeDasharray={`${length} ${circumference - length}`}
                    strokeDashoffset={-offset}
                    transform="rotate(-90 80 80)"
                  />
                );
                offset += length;
                return segment;
              })
            : null}
          <text x="80" y="86" textAnchor="middle" className="donut-center">
            {total}
          </text>
        </svg>
        <ul className="donut-legend">
          {SEVERITY_ORDER.map((sev) => (
            <li key={sev}>
              <span className="legend-dot" style={{ background: SEVERITY_COLORS[sev] }} />
              <span className={`severity severity-${sev}`}>{sev}</span>
              <strong>{dist[sev]}</strong>
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}

function AttackSurfacePanel({ surface }: { surface: AttackSurfaceResponse }) {
  const { t } = useLocale();
  return (
    <article className="panel-card">
      <h3>{t('dashboard_attack_surface')}</h3>
      {surface.endpoints.length === 0 ? (
        <p className="muted">{t('surface_no_endpoints')}</p>
      ) : (
        <ul className="surface-list">
          {surface.endpoints.slice(0, 12).map((e) => (
            <li key={`${e.host}-${e.method}-${e.path_template}`} className="surface-row">
              <div className="surface-main">
                <span className="surface-method">{e.method}</span>
                <span className="surface-path">{e.host}{e.path_template}</span>
              </div>
              <div className="surface-meta">
                {e.max_severity ? (
                  <span className={`severity severity-${e.max_severity}`}>{e.max_severity}</span>
                ) : null}
                <span className="muted">{e.finding_count} {t('surface_findings')}</span>
                <span className="muted">{e.has_auth_boundary ? t('surface_auth') : t('surface_no_auth')}</span>
                <span className="surface-score" title={t('surface_priority')}>★ {e.priority_score.toFixed(1)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

function RecentTimeline({
  findings,
  onSelectAnalysis,
}: {
  findings: RecentFinding[];
  onSelectAnalysis: (id: string) => void;
}) {
  const { t } = useLocale();
  return (
    <article className="panel-card">
      <h3>{t('dashboard_recent')}</h3>
      {findings.length === 0 ? (
        <p className="muted">{t('dashboard_no_recent')}</p>
      ) : (
        <ul className="timeline">
          {findings.map((f, i) => (
            <li
              key={`${f.analysis_id}-${i}`}
              className="timeline-item"
              onClick={() => onSelectAnalysis(f.analysis_id)}
              role="button"
              tabIndex={0}
            >
              <span className={`severity severity-${f.severity}`}>{f.severity}</span>
              <div className="timeline-body">
                <strong>{f.title}</strong>
                <span className="muted">{f.target_url || f.owasp_category || ''}</span>
              </div>
              <span className="timeline-time muted">{relativeTime(f.created_at, t)}</span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

function ArchitecturePanel({ hosts }: { hosts: string[] }) {
  const { t } = useLocale();
  const [host, setHost] = useState('');
  const [profile, setProfile] = useState<ArchitectureProfile | null>(null);
  const [roadmap, setRoadmap] = useState<RoadmapResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!host && hosts.length > 0) setHost(hosts[0]);
  }, [hosts, host]);

  useEffect(() => {
    if (!host) return;
    fetchArchitecture(host)
      .then((p) => setProfile(Array.isArray(p?.system_types) ? p : null))
      .catch(() => setProfile(null));
    setRoadmap(null);
  }, [host]);

  async function generate() {
    if (!host) return;
    setLoading(true);
    setFailed(false);
    try {
      const result = await fetchRoadmap(host);
      setRoadmap(result);
      if (result.llm_status === 'failed') setFailed(true);
    } catch {
      setFailed(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <article className="panel-card">
      <h3>
        <Compass aria-hidden="true" size={16} /> {t('arch_title')}
      </h3>
      <label className="arch-host">
        {t('arch_select_host')}
        <select value={host} onChange={(e) => setHost(e.target.value)}>
          {hosts.length === 0 ? <option value="">—</option> : null}
          {hosts.map((h) => (
            <option key={h} value={h}>{h}</option>
          ))}
        </select>
      </label>

      {profile ? (
        <dl className="arch-facts">
          <dt>{t('arch_system_types')}</dt>
          <dd>{profile.system_types?.join(', ') || t('arch_unknown')}</dd>
          <dt>{t('arch_auth')}</dt>
          <dd>{profile.auth_methods?.join(', ') || t('arch_unknown')}</dd>
          <dt>{t('arch_tech')}</dt>
          <dd>{profile.tech_stack?.join(', ') || t('arch_unknown')}</dd>
          <dt>{t('arch_confidence')}</dt>
          <dd>{Math.round((profile.confidence ?? 0) * 100)}%</dd>
        </dl>
      ) : null}

      <button type="button" className="secondary-action" disabled={!host || loading} onClick={generate}>
        <Sparkles aria-hidden="true" size={14} />
        {loading ? t('roadmap_generating') : t('arch_generate_roadmap')}
      </button>

      {failed ? (
        <div className="notice result-error" role="alert">
          <AlertCircle aria-hidden="true" size={14} />
          {t('roadmap_failed')}
        </div>
      ) : null}

      {roadmap && !failed ? <RoadmapView roadmap={roadmap} /> : null}
    </article>
  );
}

function RoadmapView({ roadmap }: { roadmap: RoadmapResponse }) {
  const { t } = useLocale();
  if (roadmap.stages.length === 0) {
    return <p className="muted">{roadmap.notes || t('roadmap_empty')}</p>;
  }
  return (
    <div className="roadmap">
      <h4>{t('roadmap_title')}</h4>
      {roadmap.stages.map((stage, si) => (
        <div className="roadmap-stage" key={`${stage.stage}-${si}`}>
          <div className="roadmap-stage-head">
            <span className="roadmap-num">{si + 1}</span>
            <strong>{stage.stage}</strong>
          </div>
          {stage.objective ? <p className="muted">{t('roadmap_objective')}: {stage.objective}</p> : null}
          {stage.steps.map((step, ki) => (
            <div className="roadmap-step" key={`${step.target}-${ki}`}>
              <div className="roadmap-step-head">
                <code>{step.target}</code>
                <span className="severity severity-medium">{step.suspected_vuln}</span>
                {step.priority ? <span className="muted">{t('roadmap_priority')} {step.priority}</span> : null}
              </div>
              <p>{step.reason}</p>
              {step.verification_steps.length > 0 ? (
                <ol className="verify-steps">
                  {step.verification_steps.map((vs, vi) => (
                    <li key={vi}>{vs}</li>
                  ))}
                </ol>
              ) : null}
            </div>
          ))}
        </div>
      ))}
      {roadmap.notes ? <p className="muted roadmap-note">{roadmap.notes}</p> : null}
    </div>
  );
}

function relativeTime(iso: string, t: (key: LocaleKeys) => string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const diff = Date.now() - then;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return t('time_now');
  if (minutes < 60) return `${minutes}${t('time_minute_suffix')}`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}${t('time_hour_suffix')}`;
  return `${Math.floor(hours / 24)}${t('time_day_suffix')}`;
}
