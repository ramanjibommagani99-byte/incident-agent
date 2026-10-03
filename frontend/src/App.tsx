import { useCallback, useEffect, useMemo, useState } from 'react'
import { Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, BookOpen, Check, ChevronDown, ChevronRight, Clock3, Command, ExternalLink, FileText, Filter, Gauge, Layers3, LifeBuoy, LoaderCircle, LockKeyhole, Plus, Radio, RefreshCw, Search, ShieldCheck, Sparkles, Timer, X } from 'lucide-react'

const API = '/api'
const request = async (path, options = {}) => {
  const response = await fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options })
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail || 'Request failed')
  return body
}
const timeAgo = value => {
  if (!value) return '—'
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000))
  return minutes < 1 ? 'just now' : `${minutes}m ago`
}
const titleCase = value => value?.replaceAll('_', ' ') || '—'

function App() {
  const [incidents, setIncidents] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [audit, setAudit] = useState(null)
  const [tab, setTab] = useState('Overview')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState('')
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [rows, stats, trail] = await Promise.all([request('/incidents'), request('/analytics'), request('/audit')])
      setIncidents(rows); setAnalytics(stats); setAudit(trail)
      if (selectedId) {
        try { setDetail(await request(`/incidents/${selectedId}`)) } catch { setDetail(null); setSelectedId(null) }
      }
    } catch (e) { setError(e.message) } finally { setLoading(false) }
  }, [selectedId])

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => { if (!toast) return; const timer = setTimeout(() => setToast(''), 3200); return () => clearTimeout(timer) }, [toast])

  const openIncident = async id => {
    setSelectedId(id)
    try { setDetail(await request(`/incidents/${id}`)); setTab('Overview') } catch (e) { setError(e.message) }
  }
  const simulate = async () => {
    setBusy(true); setError('')
    try { const created = await request('/simulate/bad-deploy-checkout', { method: 'POST' }); await refresh(); setSelectedId(created.id); setDetail(created); setTab('Overview'); setToast('Checkout failure injected · evidence correlated') }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  const decide = async (action, decision) => {
    setBusy(true)
    try { const result = await request(`/actions/${action.id}/${decision}`, { method: 'POST', body: JSON.stringify({ decided_by: 'On-call engineer' }) }); setDetail(result.incident); await refresh(); setToast(decision === 'approve' ? 'Rollback approved · simulated resolution recorded' : 'Recommendation rejected') }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  const createPostmortem = async () => {
    if (!selectedId) return
    setBusy(true)
    try { const draft = await request(`/incidents/${selectedId}/postmortem`, { method: 'POST' }); setDetail(current => ({ ...current, postmortem: draft })); await refresh(); setToast('Postmortem draft created') }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  const filtered = useMemo(() => incidents.filter(row => `${row.title} ${row.service || ''} ${row.category} ${row.status}`.toLowerCase().includes(query.toLowerCase())), [incidents, query])
  const active = incidents.filter(row => !['Resolved', 'Closed'].includes(row.status)).length
  const sev1 = incidents.filter(row => row.severity === 'SEV1').length

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Activity size={19} /></div><div><b>signal<span>ops</span></b><small>INCIDENT COMMAND</small></div></div>
      <div className="workspace"><div className="workspace-icon">N</div><div><strong>Northstar Cloud</strong><small>Production environment</small></div><ChevronDown size={14} /></div>
      <div className="nav-label">WORKSPACE</div>
      <nav className="nav-list">
        <button className="nav-item active" onClick={() => { setSelectedId(null); setTab('Overview') }}><Layers3 size={16} /> Incidents <span className="nav-count">{active}</span></button>
        <button className="nav-item" onClick={() => setTab('Analytics')}><Gauge size={16} /> Analytics</button>
        <button className="nav-item" onClick={() => setTab('Knowledge base')}><BookOpen size={16} /> Knowledge base</button>
        <button className="nav-item" onClick={() => setTab('Audit trail')}><ShieldCheck size={16} /> Audit trail</button>
      </nav>
      <div className="sidebar-bottom"><div className="live-indicator"><span className="pulse" /> All systems operational</div><div className="user-card"><div className="avatar">JD</div><div><strong>Jordan Davis</strong><small>On-call engineer</small></div><More /></div></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="breadcrumbs"><span>Operations</span><ChevronRight size={14} /><strong>{selectedId ? 'Incident detail' : tab}</strong></div><div className="top-actions"><div className="env-pill"><span /> PRODUCTION</div><button className="icon-button" title="Refresh" onClick={refresh}><RefreshCw size={16} className={loading ? 'spin' : ''} /></button><div className="top-avatar">JD</div></div></header>
      <div className="content">
        {error && <div className="error-banner"><AlertTriangle size={16} />{error}<button onClick={() => setError('')}><X size={14} /></button></div>}
        {!selectedId && tab === 'Overview' && <>
          <div className="page-heading"><div><div className="eyebrow">MONDAY, OCTOBER 12, 2026 <span className="dot-sep">·</span> ON-CALL SHIFT</div><h1>Incident overview</h1><p>Monitor, investigate, and resolve production incidents.</p></div><button className="button button-primary" onClick={simulate} disabled={busy}><Radio size={15} />{busy ? 'Injecting…' : 'Simulate incident'}<span className="button-hotkey">⌘ I</span></button></div>
          <div className="stat-grid">
            <StatCard title="Active incidents" value={active} hint={active ? 'Requires attention' : 'No active incidents'} icon={<Activity size={17} />} tone="blue" />
            <StatCard title="Critical · SEV-1" value={sev1} hint={sev1 ? 'Immediate response' : 'All clear'} icon={<AlertTriangle size={17} />} tone="red" trend={sev1 ? 'Urgent' : null} />
            <StatCard title="Mean time to resolve" value={analytics?.mttr_seconds ? `${Math.max(1, Math.round(analytics.mttr_seconds / 60))}m` : '—'} hint={`${analytics?.resolved_count || 0} resolved incidents`} icon={<Timer size={17} />} tone="purple" />
            <StatCard title="Audit integrity" value={audit?.verified ? 'Verified' : '—'} hint={`${audit?.events?.length || 0} events · hash chained`} icon={<ShieldCheck size={17} />} tone="green" verified={audit?.verified} />
          </div>
          <div className="section-title-row"><div><h2>Incident queue <span className="counter">{filtered.length}</span></h2><p>Live view of production events</p></div><button className="button button-quiet" onClick={refresh}><RefreshCw size={14} /> Refresh</button></div>
          <div className="table-card"><div className="table-toolbar"><label className="search-box"><Search size={15} /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search incidents…" /><kbd>⌘ K</kbd></label><button className="filter-button"><Filter size={14} /> Filters <ChevronDown size={13} /></button><div className="view-toggle"><button className="selected">All</button><button>Mine</button></div></div>
            <div className="table-wrap"><table><thead><tr><th>INCIDENT</th><th>SEVERITY</th><th>STATUS</th><th>SERVICE</th><th>ASSIGNEE</th><th>UPDATED</th><th></th></tr></thead><tbody>
              {filtered.map(row => <tr key={row.id} onClick={() => openIncident(row.id)} className="incident-row"><td><div className="incident-title"><span className={`severity-mark ${row.severity.toLowerCase()}`} /><div><strong>{row.title}</strong><small>{row.id.slice(0, 8)} · {row.category || 'Unclassified'}</small></div></div></td><td><Severity value={row.severity} /></td><td><Status value={row.status} /></td><td><span className="service-name"><span className="service-dot" />{row.service || '—'}</span></td><td><span className="assignee"><span className="mini-avatar">JD</span>{row.assignee || 'Unassigned'}</span></td><td className="muted-cell">{timeAgo(row.created_at)}</td><td><ChevronRight size={15} className="row-chevron" /></td></tr>)}
              {!filtered.length && <tr><td colSpan="7"><EmptyState onSimulate={simulate} busy={busy} /></td></tr>}
            </tbody></table></div><div className="table-footer"><span>Showing <b>{filtered.length}</b> of <b>{incidents.length}</b> incidents</span><span className="live-note"><span className="pulse" /> Live updates <span className="footer-divider">·</span> Last refreshed just now</span></div></div>
          <div className="bottom-grid"><div className="panel"><div className="panel-heading"><div><h3>Incident activity</h3><p>Recent events across your services</p></div><button className="text-link" onClick={() => setTab('Audit trail')}>View audit trail <ChevronRight size={13} /></button></div><ActivityList events={incidents.flatMap(row => (row.timeline || []).map(event => ({ ...event, incidentTitle: row.title }))).slice(-4).reverse()} /></div><div className="panel ai-promo"><div className="promo-icon"><Sparkles size={18} /></div><div><div className="promo-label">AI RESPONSE ENGINE</div><h3>Evidence first. Human approved.</h3><p>Every recommendation links back to logs. Sensitive actions wait for your approval.</p><div className="promo-foot"><ShieldCheck size={13} /> Model actions are always gated</div></div></div></div>
        </>}
        {selectedId && detail && <IncidentDetail detail={detail} busy={busy} decide={decide} createPostmortem={createPostmortem} tab={tab} setTab={setTab} />}
        {!selectedId && tab === 'Analytics' && <AnalyticsPage stats={analytics} incidents={incidents} />}
        {!selectedId && tab === 'Knowledge base' && <KnowledgePage />}
        {!selectedId && tab === 'Audit trail' && <AuditPage audit={audit} />}
      </div>
      <footer className="app-footer"><span><span className="pulse" /> API connected <span className="footer-divider">·</span> Demo environment</span><span>SignalOps Incident Command <span className="footer-divider">·</span> v0.1.0</span></footer>
    </main>
    {toast && <div className="toast"><Check size={16} />{toast}</div>}
  </div>
}

function More() { return <span className="more-dots">···</span> }
function StatCard({ title, value, hint, icon, tone, trend, verified }) { return <div className="stat-card"><div className="stat-top"><span>{title}</span><span className={`stat-icon ${tone}`}>{icon}</span></div><div className="stat-value">{value}{trend && <span className="trend-badge"><ArrowUpRight size={12} />{trend}</span>}</div><div className="stat-hint">{verified !== undefined && <span className={verified ? 'verify-ok' : 'verify-bad'}>{verified ? <Check size={12} /> : <X size={12} />}</span>}{hint}</div></div> }
function Severity({ value }) { const sev = value || 'SEV3'; return <span className={`severity-pill ${sev.toLowerCase()}`}><span />{sev}</span> }
function Status({ value }) { const cls = (value || 'New').toLowerCase().replaceAll(' ', '-'); return <span className={`status-pill ${cls}`}><span className="status-dot" />{value}</span> }
function EmptyState({ onSimulate, busy }) { return <div className="empty-state"><div className="empty-icon"><LifeBuoy size={20} /></div><strong>No incidents yet</strong><span>Run the demo scenario to see the complete response workflow.</span><button className="button button-primary button-small" onClick={onSimulate} disabled={busy}><Radio size={14} /> Simulate checkout failure</button></div> }
function ActivityList({ events }) { if (!events.length) return <div className="activity-empty">No incident events yet. Start a simulation to populate the timeline.</div>; return <div className="activity-list">{events.map(event => <div className="activity-row" key={event.id}><span className={`activity-icon ${event.actor}`}><Activity size={13} /></span><span><strong>{event.detail}</strong><small>{event.incidentTitle} <span>·</span> {event.actor} <span>·</span> {timeAgo(event.timestamp)}</small></span></div>)}</div> }

function IncidentDetail({ detail, busy, decide, createPostmortem, tab, setTab }) {
  const [postmortem, setPostmortem] = useState(detail.postmortem || null)
  const [kb, setKb] = useState([])
  useEffect(() => { if (tab === 'Knowledge base') request('/kb').then(setKb).catch(() => {}) }, [tab])
  const timeline = [...(detail.timeline || [])].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
  const pending = (detail.proposed_actions || []).find(action => action.status === 'pending')
  const stage = ['New', 'Triaged', 'Investigating', 'Awaiting Approval', 'Mitigated', 'Resolved', 'Closed']
  const activeIndex = stage.indexOf(detail.status)
  return <>
    <div className="detail-back"><button onClick={() => { window.history.replaceState(null, '', '/'); location.reload() }}>← Incidents</button><span>/</span><span>{detail.id.slice(0, 8)}</span><span className="detail-live"><span className="pulse" /> LIVE</span></div>
    <div className="detail-heading"><div><div className="detail-title-line"><span className={`severity-mark ${detail.severity.toLowerCase()}`} /><h1>{detail.title}</h1></div><p>{detail.id} <span>·</span> Opened {timeAgo(detail.created_at)} <span>·</span> {detail.service || 'Unknown service'}</p></div><button className="button button-quiet" onClick={() => navigator.clipboard?.writeText(detail.id)}><Command size={14} /> Copy ID</button></div>
    <div className="stepper">{stage.map((s, i) => <div className={`step ${i < activeIndex ? 'complete' : i === activeIndex ? 'current' : ''}`} key={s}><span className="step-mark">{i < activeIndex ? <Check size={11} /> : i + 1}</span><span>{s}</span>{i < stage.length - 1 && <i />}</div>)}</div>
    <div className="detail-tabs">{['Overview', 'Evidence', 'Postmortem', 'Knowledge base'].map(item => <button className={tab === item ? 'selected' : ''} onClick={() => setTab(item)} key={item}>{item}{item === 'Evidence' && <span className="tab-count">{detail.evidence?.length || 0}</span>}</button>)}</div>
    {tab === 'Overview' && <div className="detail-grid"><div className="detail-main"><div className="panel ai-analysis"><div className="ai-card-head"><div className="ai-head-icon"><Sparkles size={17} /></div><div><strong>AI incident analysis</strong><small>Rule-based fallback · evidence-linked output</small></div><span className="confidence"><span className="confidence-dot" />{Math.round((detail.confidence || 0) * 100)}% confidence</span></div><div className="analysis-summary"><div className="analysis-label">SUMMARY</div><p>{detail.ai_summary || 'Analysis is being prepared.'}</p></div><div className="analysis-columns"><div><div className="analysis-label">PROBABLE ROOT CAUSE</div><p className="root-cause">{detail.probable_root_cause || 'More evidence is needed.'}</p></div><div><div className="analysis-label">CLASSIFICATION</div><div className="class-tags"><Severity value={detail.severity} /><span className="category-tag">{detail.category}</span><span className="priority-tag">P{detail.priority}</span></div></div></div><div className="evidence-ref"><FileText size={14} /><span>Grounded in <b>{detail.evidence?.length || 0} log entries</b></span><button onClick={() => setTab('Evidence')}>Review evidence <ChevronRight size={13} /></button></div></div>
      <div className="panel evidence-panel"><div className="panel-heading"><div><h3>Correlated evidence</h3><p>Signals linked to this incident</p></div><button className="text-link" onClick={() => setTab('Evidence')}>View all <ChevronRight size={13} /></button></div><EvidenceList rows={(detail.evidence || []).slice(0, 4)} /></div>
      {pending && <div className="panel approval-panel"><div className="approval-heading"><div className="approval-icon"><LockKeyhole size={16} /></div><div><strong>Approval required</strong><small>This action changes production state and needs your review.</small></div><span className="sensitive-badge">SENSITIVE</span></div><div className="action-proposal"><span className="action-num">01</span><div><strong>{pending.description}</strong><small>Risk assessment: service rollback · customer impact mitigation</small></div></div><div className="approval-warning"><AlertTriangle size={14} /><span>Approval triggers a <b>simulated</b> rollback and resolution. No production system is connected.</span></div><div className="approval-actions"><button className="button button-danger-quiet" onClick={() => decide(pending, 'reject')} disabled={busy}><X size={14} /> Reject</button><button className="button button-primary" onClick={() => decide(pending, 'approve')} disabled={busy}><Check size={14} /> Approve rollback</button></div></div>}
      <div className="panel postmortem-cta"><div className="post-icon"><FileText size={17} /></div><div><strong>Post-incident review</strong><small>Draft a timeline-based postmortem from the incident evidence.</small></div><button className="button button-quiet" onClick={createPostmortem} disabled={busy}><Sparkles size={14} /> Draft postmortem</button></div>
      </div><div className="detail-side"><div className="panel metadata-panel"><div className="panel-heading"><div><h3>Incident details</h3><p>Ownership and impact</p></div><More /></div><MetaRow label="STATUS"><Status value={detail.status} /></MetaRow><MetaRow label="SEVERITY"><Severity value={detail.severity} /></MetaRow><MetaRow label="SERVICE"><span className="service-name"><span className="service-dot" />{detail.service || '—'}</span></MetaRow><MetaRow label="ASSIGNEE"><span className="assignee"><span className="mini-avatar">JD</span>{detail.assignee || 'Unassigned'}</span></MetaRow><MetaRow label="CREATED"><span>{new Date(detail.created_at).toLocaleString()}</span></MetaRow><MetaRow label="SOURCE"><span className="source-tag"><Radio size={12} /> {detail.source}</span></MetaRow></div><div className="panel timeline-panel"><div className="panel-heading"><div><h3>Timeline</h3><p>{timeline.length} recorded events</p></div><button className="icon-button small"><ChevronDown size={14} /></button></div><div className="timeline-list">{timeline.map(event => <div className="timeline-item" key={event.id}><span className={`timeline-marker ${event.actor}`} /><div><strong>{event.detail}</strong><small>{event.actor} <span>·</span> {new Date(event.timestamp).toLocaleTimeString()}</small></div></div>)}</div></div></div></div>}
    {tab === 'Evidence' && <div className="panel full-panel"><div className="panel-heading"><div><h3>Evidence log</h3><p>Correlated entries attached to this incident</p></div><span className="evidence-count">{detail.evidence?.length || 0} entries</span></div><EvidenceList rows={detail.evidence || []} expanded /></div>}
    {tab === 'Postmortem' && <div className="panel full-panel"><div className="panel-heading"><div><h3>Post-incident review</h3><p>Draft generated from incident timeline and evidence</p></div><button className="button button-primary button-small" onClick={createPostmortem} disabled={busy}><Sparkles size={14} /> Generate draft</button></div><Postmortem draft={postmortem} /></div>}
    {tab === 'Knowledge base' && <div className="panel full-panel"><div className="panel-heading"><div><h3>Related knowledge</h3><p>Runbooks and learnings that may help resolve this incident</p></div></div>{kb.length ? kb.map(article => <article className="kb-article" key={article.id}><span className="category-tag">{article.category}</span><h3>{article.title}</h3><p>{article.content_md}</p></article>) : <div className="activity-empty">Loading knowledge articles…</div>}</div>}
  </>
}

function EvidenceList({ rows, expanded }) { if (!rows.length) return <div className="activity-empty">No linked log evidence is available yet.</div>; return <div className="evidence-list">{rows.map(row => <div className="evidence-row" key={row.id}><span className={`log-level ${(row.level || 'info').toLowerCase()}`}>{row.level}</span><span className="log-time">{new Date(row.timestamp).toLocaleTimeString()}</span><span className="log-service">{row.service}</span><code>{row.message}</code><span className="trace-ref">{row.trace_id || row.id.slice(0, 8)}</span>{expanded && <span className="log-id">{row.id}</span>}</div>)}</div> }
function MetaRow({ label, children }) { return <div className="meta-row"><span>{label}</span><div>{children}</div></div> }
function Postmortem({ draft }) { if (!draft) return <div className="postmortem-empty"><div className="empty-icon"><FileText size={20} /></div><strong>No draft yet</strong><span>Generate a postmortem after reviewing the incident outcome.</span></div>; return <div className="postmortem-doc"><div className="draft-stamp"><FileText size={13} /> AI DRAFT · HUMAN REVIEW REQUIRED</div><h2>{draft.title}</h2><div className="post-section"><h4>Impact</h4><p>{draft.impact}</p></div><div className="post-section"><h4>Root cause</h4><p>{draft.root_cause}</p></div><div className="post-section"><h4>Detection</h4><p>{draft.detection}</p></div><div className="post-section"><h4>Resolution</h4><p>{draft.resolution}</p></div><div className="post-section"><h4>Follow-up actions</h4><ul>{draft.follow_up?.map(item => <li key={item}>{item}</li>)}</ul></div><div className="draft-disclaimer"><AlertTriangle size={14} /> This draft is based on captured incident evidence. Review and correct it before sharing.</div></div> }
function AnalyticsPage({ stats, incidents }) { return <><div className="page-heading"><div><div className="eyebrow">OPERATIONS INTELLIGENCE</div><h1>Analytics</h1><p>Incident patterns and response performance.</p></div></div><div className="stat-grid"><StatCard title="Total incidents" value={stats?.total_incidents || 0} hint="Across this demo environment" icon={<Layers3 size={17} />} tone="blue"/><StatCard title="Resolved" value={stats?.resolved_count || 0} hint="Successfully mitigated" icon={<Check size={17} />} tone="green"/><StatCard title="Mean time to resolve" value={stats?.mttr_seconds ? `${Math.round(stats.mttr_seconds / 60)}m` : '—'} hint="Resolved incidents only" icon={<Timer size={17} />} tone="purple"/><StatCard title="Critical incidents" value={stats?.by_severity?.SEV1 || 0} hint="SEV-1 classification" icon={<AlertTriangle size={17} />} tone="red"/></div><div className="two-panels"><div className="panel"><div className="panel-heading"><div><h3>By severity</h3><p>Distribution of incident priority</p></div></div><BarRows rows={Object.entries(stats?.by_severity || {})} /></div><div className="panel"><div className="panel-heading"><div><h3>By category</h3><p>Incident type breakdown</p></div></div><BarRows rows={Object.entries(stats?.by_category || {})} /></div></div><div className="panel full-panel"><div className="panel-heading"><div><h3>Recent incidents</h3><p>Latest activity from the incident queue</p></div></div><div className="compact-list">{incidents.slice(0, 6).map(row => <div key={row.id}><Severity value={row.severity}/><strong>{row.title}</strong><Status value={row.status}/><span>{timeAgo(row.created_at)}</span></div>)}</div></div></> }
function BarRows({ rows }) { const max = Math.max(1, ...rows.map(([, value]) => value)); if (!rows.length) return <div className="activity-empty">No incident data yet.</div>; return <div className="bar-list">{rows.map(([label, value]) => <div className="bar-row" key={label}><span>{label}</span><div className="bar-track"><i style={{ width: `${Math.max(4, value / max * 100)}%` }}/></div><b>{value}</b></div>)}</div> }
function KnowledgePage() { const [articles, setArticles] = useState([]); const [query, setQuery] = useState(''); useEffect(() => { request(`/kb${query ? `?q=${encodeURIComponent(query)}` : ''}`).then(setArticles).catch(() => {}) }, [query]); return <><div className="page-heading"><div><div className="eyebrow">OPERATIONS PLAYBOOK</div><h1>Knowledge base</h1><p>Runbooks and learnings from previous incidents.</p></div></div><div className="panel full-panel"><div className="table-toolbar"><label className="search-box"><Search size={15}/><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search articles…"/></label><span className="evidence-count">{articles.length} articles</span></div>{articles.map(article => <article className="kb-article" key={article.id}><span className="category-tag">{article.category}</span><h3>{article.title}</h3><p>{article.content_md}</p></article>)}{!articles.length && <div className="activity-empty">No matching articles found.</div>}</div></> }
function AuditPage({ audit }) { return <><div className="page-heading"><div><div className="eyebrow">TAMPER-EVIDENT EVENT LOG</div><h1>Audit trail</h1><p>Every state transition and AI finding is recorded with a verifiable hash chain.</p></div><div className={`chain-badge ${audit?.verified ? 'verified' : 'broken'}`}>{audit?.verified ? <Check size={14}/> : <AlertTriangle size={14}/>} {audit?.verified ? 'Chain verified' : 'Verification unavailable'}</div></div><div className="panel full-panel"><div className="panel-heading"><div><h3>Recorded events</h3><p>Append-only incident activity</p></div><span className="evidence-count">{audit?.events?.length || 0} events</span></div><div className="audit-list">{[...(audit?.events || [])].reverse().map(event => <div className="audit-row" key={event.id}><div className="audit-icon"><ShieldCheck size={15}/></div><div className="audit-info"><strong>{titleCase(event.action)}</strong><small>{event.actor} <span>·</span> {new Date(event.timestamp).toLocaleString()}</small></div><code>{event.hash?.slice(0, 14)}…</code><ChevronRight size={14}/></div>)}{!audit?.events?.length && <div className="activity-empty">Audit events will appear here as incidents are processed.</div>}</div></div></> }

export default App
