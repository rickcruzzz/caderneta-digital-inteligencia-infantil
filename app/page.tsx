"use client";

import {
  Activity, Baby, BarChart3, ClipboardCheck, FileText, HeartPulse, LogOut,
  RefreshCw, Search, ShieldCheck, Stethoscope, Upload, Users,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

type User = { username: string; role: "ADMIN" | "PROFISSIONAL" | "LEITURA" };
type Row = Record<string, any>;
type Page = "Visão geral" | "Inteligência de dados" | "Central de monitoramento" | "Crianças" | "Resumo digital de alta" | "Integração" | "Auditoria";

const navigation: { name: Page; icon: typeof Activity; admin?: boolean }[] = [
  { name: "Visão geral", icon: Activity },
  { name: "Inteligência de dados", icon: BarChart3 },
  { name: "Central de monitoramento", icon: ClipboardCheck },
  { name: "Crianças", icon: Baby },
  { name: "Resumo digital de alta", icon: FileText },
  { name: "Integração", icon: Upload },
  { name: "Auditoria", icon: ShieldCheck, admin: true },
];

async function api<T = Row>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: "include",
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail?.message || body.error?.message || "Não foi possível concluir a operação.";
    throw new Error(detail);
  }
  return body as T;
}

function formatDate(value: unknown) {
  if (!value) return "Sem informação";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(date);
}

function statusClass(value: string) {
  if (["RESOLVIDO", "REALIZADO", "VALIDADO", "PROCESSADO"].includes(value)) return "green";
  if (["PENDENTE", "NOVO", "EM_ACOMPANHAMENTO", "ATUALIZADO"].includes(value)) return "amber";
  if (["DESCARTADO", "NAO_REALIZADO_CONFIRMADO_PELA_ORIGEM"].includes(value)) return "red";
  return "blue";
}

function Empty({ children }: { children: React.ReactNode }) {
  return <div className="empty">{children}</div>;
}

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [page, setPage] = useState<Page>("Visão geral");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loginError, setLoginError] = useState("");
  const [reloadId, setReloadId] = useState(0);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [dashboard, setDashboard] = useState<Row>({ metrics: {} });
  const [children, setChildren] = useState<Row[]>([]);
  const [events, setEvents] = useState<Row[]>([]);
  const [monitorings, setMonitorings] = useState<Row[]>([]);
  const [summaries, setSummaries] = useState<Row[]>([]);
  const [audit, setAudit] = useState<Row[]>([]);
  const [reports, setReports] = useState<Row>({});
  const [rules, setRules] = useState<Row[]>([]);
  const [search, setSearch] = useState("");
  const [unitFilter, setUnitFilter] = useState("Todas");
  const [typeFilter, setTypeFilter] = useState("Todos");
  const [statusFilter, setStatusFilter] = useState("Todos");
  const [selectedChild, setSelectedChild] = useState<Row | null>(null);
  const [childDetail, setChildDetail] = useState<Row | null>(null);
  const [selectedMonitor, setSelectedMonitor] = useState<Row | null>(null);
  const [selectedSummary, setSelectedSummary] = useState<Row | null>(null);
  const [monitorStatus, setMonitorStatus] = useState("PENDENTE");
  const [monitorNote, setMonitorNote] = useState("");
  const [monitorReason, setMonitorReason] = useState("");

  useEffect(() => {
    let active = true;
    api<{ user: User }>("/api/v1/auth/me")
      .then(result => { if (active) setUser(result.user); })
      .catch(() => { if (active) setUser(null); })
      .finally(() => { if (active) setChecking(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!user) return;
    let active = true;
    setLoading(true);
    setError("");
    Promise.all([
      api<Row>("/api/v1/dashboard"),
      api<{ items: Row[] }>("/api/v1/criancas"),
      api<{ items: Row[] }>("/api/v1/eventos"),
      api<{ items: Row[] }>("/api/v1/monitoramentos"),
      api<{ items: Row[] }>("/api/v1/resumos-alta"),
      api<Row>("/api/v1/relatorios"),
      user.role === "ADMIN" ? api<{ items: Row[] }>("/api/v1/admin/rules") : Promise.resolve({ items: [] }),
      user.role === "ADMIN" ? api<{ items: Row[] }>("/api/v1/auditoria") : Promise.resolve({ items: [] }),
    ])
      .then(([dashboardData, childData, eventData, monitorData, summaryData, reportData, ruleData, auditData]) => {
        if (!active) return;
        setDashboard(dashboardData);
        setChildren(childData.items || []);
        setEvents(eventData.items || []);
        setMonitorings(monitorData.items || []);
        setSummaries(summaryData.items || []);
        setReports(reportData);
        setRules(ruleData.items || []);
        setAudit(auditData.items || []);
      })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : "Erro ao carregar dados."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [user, page, reloadId]);

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setLoginError("");
    try {
      const result = await api<{ user: User }>("/api/v1/auth/login", {
        method: "POST", body: JSON.stringify({ username, password }),
      });
      setUser(result.user);
      setPassword("");
    } catch (reason) {
      setLoginError(reason instanceof Error ? reason.message : "Falha no acesso.");
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    await api("/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    setUser(null);
  }

  function refresh() { setReloadId(value => value + 1); }

  async function saveMonitoring() {
    if (!selectedMonitor) return;
    setBusy(true);
    setError("");
    try {
      await api(`/api/v1/monitoramentos/${selectedMonitor._id}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: monitorStatus,
          note: monitorNote || null,
          resolution_reason: monitorReason || null,
          responsible: user?.username,
        }),
      });
      setSelectedMonitor(null);
      setMonitorReason("");
      refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao atualizar ocorrência.");
    } finally {
      setBusy(false);
    }
  }

  async function saveRule(ruleId: string, values: Row) {
    setBusy(true);
    setError("");
    try {
      await api(`/api/v1/admin/rules/${encodeURIComponent(ruleId)}`, {
        method: "PATCH",
        body: JSON.stringify(values),
      });
      refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao salvar regra.");
    } finally {
      setBusy(false);
    }
  }

  async function openChild(child: Row) {
    setSelectedChild(child);
    setChildDetail(null);
    try {
      const detail = await api<Row>(`/api/v1/criancas/${encodeURIComponent(child.external_id)}?source_system=${encodeURIComponent(child.source_system)}`);
      setChildDetail(detail);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao abrir criança.");
    }
  }

  async function generateSummary(child: Row) {
    setBusy(true);
    try {
      await api("/api/v1/resumos-alta", {
        method: "POST",
        body: JSON.stringify({ source_system: child.source_system, child_external_id: child.external_id }),
      });
      refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao gerar resumo.");
    } finally {
      setBusy(false);
    }
  }

  async function validateSummary(summary: Row) {
    setBusy(true);
    try {
      await api(`/api/v1/resumos-alta/${encodeURIComponent(summary.document_id)}/validar`, {
        method: "PATCH",
        body: JSON.stringify({ professional: user?.username, note: "Validado pela equipe." }),
      });
      refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao validar resumo.");
    } finally {
      setBusy(false);
    }
  }

  const visibleChildren = useMemo(() => children.filter(child => {
    const matchesText = !search || `${child.external_id} ${child.projections?.nascimento?.data?.nome || ""}`.toLocaleLowerCase("pt-BR").includes(search.toLocaleLowerCase("pt-BR"));
    const matchesUnit = unitFilter === "Todas" || child.unit_external_id === unitFilter;
    return matchesText && matchesUnit;
  }), [children, search, unitFilter]);

  const visibleEvents = useMemo(() => events.filter(event => {
    const matchesUnit = unitFilter === "Todas" || event.unit_external_id === unitFilter;
    const matchesType = typeFilter === "Todos" || event.event_type === typeFilter;
    const status = String(event.data?.status || "");
    const matchesStatus = statusFilter === "Todos" || status === statusFilter;
    return matchesUnit && matchesType && matchesStatus;
  }), [events, unitFilter, typeFilter, statusFilter]);

  if (checking) return <div className="loading">Conectando à Caderneta Digital…</div>;
  if (!user) {
    return (
      <main className="login-page">
        <section className="login-brand">
          <div>
            <div className="login-mark"><HeartPulse size={25} /></div>
            <p className="eyebrow" style={{ color: "#acd7ca", marginTop: 24 }}>CUIDADO INFANTIL</p>
            <h1>Caderneta Digital</h1>
            <p>Inteligência e acompanhamento para apoiar a continuidade do cuidado infantil.</p>
          </div>
          <small>Camada complementar. Os registros oficiais permanecem no sistema de origem.</small>
        </section>
        <section className="login-panel">
          <form className="login-card" onSubmit={submitLogin}>
            <h2>Entrar</h2>
            <p>Acesso restrito a profissionais autorizados.</p>
            <div className="login-form">
              <div className="field"><label htmlFor="username">Usuário</label><input id="username" autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} required /></div>
              <div className="field"><label htmlFor="password">Senha</label><input id="password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required /></div>
              {loginError && <div className="notice error">{loginError}</div>}
              <button className="btn primary" disabled={busy}>{busy ? "Verificando…" : "Acessar"}</button>
            </div>
            <div className="footer-note">Use dados sintéticos neste ambiente de demonstração.</div>
          </form>
        </section>
      </main>
    );
  }

  const metricEntries = Object.entries(dashboard.metrics || {});
  const units = ["Todas", ...new Set(children.map(child => child.unit_external_id).filter(Boolean))];
  const eventTypes = ["Todos", ...new Set(events.map(event => event.event_type).filter(Boolean))];
  const eventStatuses = ["Todos", ...new Set(events.map(event => event.data?.status).filter(Boolean))];

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><HeartPulse size={20} /></div><div><div className="brand-name">Caderneta Digital</div><div className="brand-sub">Inteligência e monitoramento</div></div></div>
        <div className="nav-label">Acompanhamento</div>
        <nav className="nav">
          {navigation.filter(item => !item.admin || user.role === "ADMIN").map(item => {
            const Icon = item.icon;
            return <button key={item.name} className={page === item.name ? "active" : ""} onClick={() => setPage(item.name)}><Icon size={16} />{item.name}</button>;
          })}
        </nav>
        <div className="sidebar-foot"><div className="user-row"><span className="user-name">{user.username} · {user.role}</span><button className="logout" aria-label="Sair" title="Sair" onClick={logout}><LogOut size={16} /></button></div><div className="footer-note">Dados recebidos do sistema de origem</div></div>
      </aside>
      <main className="main">
        <header className="topbar"><div className="breadcrumb">Caderneta Digital <span aria-hidden="true"> / </span> {page}</div><div className="top-status"><span className="status-dot" />MongoDB conectado</div></header>
        {error && <div className="notice error" role="alert">{error}<button className="btn small" onClick={() => setError("")}>Fechar</button></div>}
        <div className="page-heading"><div><div className="eyebrow">CADERNETA DIGITAL</div><h1>{page}</h1><p className="page-subtitle">{page === "Visão geral" ? "Indicadores calculados a partir dos eventos recebidos." : "Dados complementares; a origem relacional permanece oficial."}</p></div><button className="btn" onClick={refresh} disabled={loading}><RefreshCw size={14} />Atualizar</button></div>
        {loading && <div className="notice">Atualizando dados do MongoDB…</div>}
        {!loading && page === "Visão geral" && <>
          <section className="metrics">{metricEntries.map(([label, value]) => <div className="metric" key={label}><div className="metric-label">{label.replaceAll("_", " ")}</div><div className="metric-value">{typeof value === "number" && label.includes("completeness") ? `${value}%` : String(value)}</div><div className="metric-note">Base caderneta_digital</div></div>)}</section>
          <section className="grid-2"><div className="panel"><div className="panel-head"><h2>Eventos recebidos</h2><span className="panel-caption">Por tipo</span></div>{(dashboard.events_by_type || []).length ? <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={dashboard.events_by_type}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7eeeb" /><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis allowDecimals={false} tick={{ fontSize: 10 }} /><Tooltip /><Bar dataKey="count" fill="#147d77" radius={[4,4,0,0]} /></BarChart></ResponsiveContainer></div> : <Empty>Aguardando eventos da origem.</Empty>}</div><div className="panel"><div className="panel-head"><h2>Pendências por unidade</h2><span className="panel-caption">Em aberto</span></div>{(dashboard.monitorings_by_unit || []).length ? <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={dashboard.monitorings_by_unit}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7eeeb" /><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis allowDecimals={false} tick={{ fontSize: 10 }} /><Tooltip /><Bar dataKey="count" fill="#d08a31" radius={[4,4,0,0]} /></BarChart></ResponsiveContainer></div> : <Empty>Sem acompanhamentos em aberto.</Empty>}</div></section>
        </>}
        {!loading && page === "Inteligência de dados" && <>
          <div className="panel"><div className="filters"><div className="field"><label>Unidade</label><select value={unitFilter} onChange={event => setUnitFilter(event.target.value)}>{units.map(item => <option key={item}>{item}</option>)}</select></div><div className="field"><label>Tipo de evento</label><select value={typeFilter} onChange={event => setTypeFilter(event.target.value)}>{eventTypes.map(item => <option key={item}>{item}</option>)}</select></div><div className="field"><label>Status de origem</label><select value={statusFilter} onChange={event => setStatusFilter(event.target.value)}>{eventStatuses.map(item => <option key={item}>{item}</option>)}</select></div><div className="field grow"><label>Identificador</label><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Pesquisar criança ou evento" /></div></div><div className="panel-head"><h2>Qualidade e recebimentos</h2><span className="panel-caption">{visibleEvents.length} eventos</span></div>{visibleEvents.length ? <div className="table-wrap"><table><thead><tr><th>Tipo</th><th>ID do evento</th><th>Criança</th><th>Unidade</th><th>Estado</th><th>Ocorrido em</th></tr></thead><tbody>{visibleEvents.filter(event => !search || `${event.child_external_id} ${event.event_id}`.toLowerCase().includes(search.toLowerCase())).map(event => <tr key={`${event.source_system}:${event.event_id}`}><td>{event.event_type}</td><td className="mono">{event.event_id}</td><td>{event.child_external_id || "Sem vínculo"}</td><td>{event.unit_external_id || "Sem informação"}</td><td><span className={`badge ${statusClass(event.processing_status || event.data?.status || "")}`}>{event.processing_status || event.data?.status || "Sem status"}</span></td><td>{formatDate(event.occurred_at)}</td></tr>)}</tbody></table></div> : <Empty>Sem eventos para os filtros atuais. Ausência de registro não confirma ausência de procedimento.</Empty>}</div>
          <div className="grid-2" style={{ marginTop: 16 }}><div className="panel"><h2>Monitoramentos por status</h2><div className="chart-wrap">{reports.monitorings_by_status?.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={reports.monitorings_by_status}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7eeeb" /><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis allowDecimals={false} tick={{ fontSize: 10 }} /><Tooltip /><Bar dataKey="count" fill="#426d8e" radius={[4,4,0,0]} /></BarChart></ResponsiveContainer> : <Empty>Sem dados de monitoramento.</Empty>}</div></div><div className="panel"><h2>Campos sem informação</h2>{children.length ? <div className="table-wrap"><table><thead><tr><th>Criança</th><th>Unidade</th><th>Lacunas identificadas</th></tr></thead><tbody>{children.map(child => { const birth = child.projections?.nascimento?.data || {}; const missing = [!birth.data_nascimento && "data de nascimento", !birth.sexo && "sexo", !birth.peso_nascimento && "peso ao nascer", !child.unit_external_id && "unidade"].filter(Boolean); return missing.length ? <tr key={child.external_id}><td>{birth.nome || child.external_id}</td><td>{child.unit_external_id || "Sem informação"}</td><td>{missing.join(", ")}</td></tr> : null; })}</tbody></table></div> : <Empty>Aguardando registros de crianças.</Empty>}</div></div>
        </>}
        {!loading && page === "Central de monitoramento" && <MonitoringPanel items={monitorings} rules={rules} user={user} onSelect={item => { setSelectedMonitor(item); setMonitorStatus(item.status); setMonitorNote(item.note || ""); }} onRuleSave={saveRule} busy={busy} />}
        {!loading && page === "Crianças" && <section className="panel"><div className="filters"><div className="field grow"><label>Pesquisar</label><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Nome ou identificador externo" /></div><div className="field"><label>Unidade</label><select value={unitFilter} onChange={event => setUnitFilter(event.target.value)}>{units.map(item => <option key={item}>{item}</option>)}</select></div></div>{selectedChild ? <><div className="panel-head"><h2>{selectedChild.projections?.nascimento?.data?.nome || selectedChild.external_id}</h2><button className="btn small" onClick={() => { setSelectedChild(null); setChildDetail(null); }}>Voltar à lista</button></div>{childDetail ? <><pre className="json-panel">{JSON.stringify(childDetail.child.projections || {}, null, 2)}</pre><div className="panel-head" style={{ marginTop: 18 }}><h3>Histórico de origem</h3></div><RowsTable rows={childDetail.events} columns={[ ["event_type", "Tipo"], ["event_id", "Evento"], ["occurred_at", "Ocorrido em"], ["version", "Versão"] ]} /><div className="panel-head" style={{ marginTop: 18 }}><h3>Monitoramentos</h3></div><RowsTable rows={childDetail.monitorings} columns={[["type", "Ocorrência"],["data_state","Estado dos dados"],["priority","Prioridade"],["status","Status"]]} /></> : <Empty>Carregando detalhes…</Empty>}</> : visibleChildren.length ? <RowsTable rows={visibleChildren} columns={[["external_id","Identificador"],["source_system","Origem"],["unit_external_id","Unidade"],["updated_at","Atualizado"]]} onRow={openChild} /> : <Empty>Nenhuma criança recebida.</Empty>}</section>}
        {!loading && page === "Resumo digital de alta" && <SummaryPanel children={children} summaries={summaries} user={user} selected={selectedSummary} onSelect={setSelectedSummary} onGenerate={generateSummary} onValidate={validateSummary} busy={busy} />}
        {!loading && page === "Integração" && <IntegrationPanel events={events} />}
        {!loading && page === "Auditoria" && <div className="monitoring-stack"><section className="panel"><div className="panel-head"><h2>Histórico de ações</h2><span className="panel-caption">Últimos registros</span></div>{audit.length ? <RowsTable rows={audit} columns={[["created_at","Data"],["actor","Ator"],["action","Ação"],["entity_type","Entidade"],["entity_id","Identificador"]]} /> : <Empty>Sem registros de auditoria.</Empty>}</section><UserAdminPanel onCreated={refresh} /></div>}
        <div className="footer-note">Dados complementares enviados pela origem. A ausência de evento significa “sem informação”.</div>
      </main>
      {selectedMonitor && <MonitorDialog item={selectedMonitor} status={monitorStatus} setStatus={setMonitorStatus} note={monitorNote} setNote={setMonitorNote} reason={monitorReason} setReason={setMonitorReason} busy={busy} onClose={() => setSelectedMonitor(null)} onSave={saveMonitoring} />}
    </div>
  );
}

function RowsTable({ rows, columns, onRow }: { rows: Row[]; columns: [string, string][]; onRow?: (row: Row) => void }) {
  return <div className="table-wrap"><table><thead><tr>{columns.map(([, label]) => <th key={label}>{label}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={row._id || row.event_id || row.document_id || row.external_id || index} onClick={() => onRow?.(row)} style={onRow ? { cursor: "pointer" } : undefined}>{columns.map(([key]) => <td key={key}>{String(row[key] ?? "Sem informação")}</td>)}</tr>)}</tbody></table></div>;
}

function MonitoringPanel({ items, rules, user, onSelect, onRuleSave, busy }: { items: Row[]; rules: Row[]; user: User; onSelect: (item: Row) => void; onRuleSave: (id: string, values: Row) => void; busy: boolean }) {
  const [status, setStatus] = useState("Todos");
  const [priority, setPriority] = useState("Todas");
  const [unit, setUnit] = useState("Todas");
  const [query, setQuery] = useState("");
  const open = items.filter(item => (status === "Todos" || item.status === status) && (priority === "Todas" || item.priority === priority) && (unit === "Todas" || item.unit_external_id === unit) && (!query || `${item.child_external_id} ${item.description}`.toLowerCase().includes(query.toLowerCase())));
  const units = ["Todas", ...new Set(items.map(item => item.unit_external_id).filter(Boolean))];
  return <div className="monitoring-stack"><section className="panel"><div className="filters"><div className="field"><label>Status</label><select value={status} onChange={event => setStatus(event.target.value)}>{["Todos", "NOVO", "EM_ACOMPANHAMENTO", "PENDENTE", "RESOLVIDO", "DESCARTADO"].map(value => <option key={value}>{value}</option>)}</select></div><div className="field"><label>Prioridade</label><select value={priority} onChange={event => setPriority(event.target.value)}>{["Todas", "BAIXA", "MEDIA", "ALTA", "CRITICA"].map(value => <option key={value}>{value}</option>)}</select></div><div className="field"><label>Unidade</label><select value={unit} onChange={event => setUnit(event.target.value)}>{units.map(value => <option key={value}>{value}</option>)}</select></div><div className="field grow"><label>Criança</label><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Identificador" /></div></div>{open.length ? <RowsTable rows={open} columns={[["child_external_id","Criança"],["unit_external_id","Unidade"],["type","Tipo"],["description","Ocorrência"],["priority","Prioridade"],["status","Status"]]} onRow={item => onSelect(item)} /> : <Empty>Nenhuma ocorrência corresponde aos filtros.</Empty>}</section>{user.role === "ADMIN" && <details className="panel rule-settings"><summary>Regras de monitoramento</summary><p className="panel-caption">Prioridade operacional não é diagnóstico. Regras com prazo ficam desligadas até aprovação local.</p>{rules.map(rule => <RuleEditor key={rule.rule_id} rule={rule} busy={busy} onSave={onRuleSave} />)}</details>}</div>;
}

function RuleEditor({ rule, busy, onSave }: { rule: Row; busy: boolean; onSave: (id: string, values: Row) => void }) {
  const [enabled, setEnabled] = useState(Boolean(rule.enabled));
  const [priority, setPriority] = useState(rule.priority || "BAIXA");
  const [days, setDays] = useState(rule.threshold_days ? String(rule.threshold_days) : "");
  const temporal = ["alta_sem_consulta", "dados_desatualizados"].includes(rule.rule_id);
  return <form className="rule-row" onSubmit={event => { event.preventDefault(); onSave(rule.rule_id, { enabled, priority, threshold_days: temporal && days ? Number(days) : null }); }}><div><strong>{rule.rule_id}</strong><div className="panel-caption">{rule.description}</div></div><label className="toggle"><input type="checkbox" checked={enabled} onChange={event => setEnabled(event.target.checked)} />Ativa</label><div className="field"><label>Prioridade</label><select value={priority} onChange={event => setPriority(event.target.value)}>{["BAIXA", "MEDIA", "ALTA", "CRITICA"].map(value => <option key={value}>{value}</option>)}</select></div>{temporal && <div className="field"><label>Intervalo aprovado (dias)</label><input type="number" min="1" max="3650" value={days} onChange={event => setDays(event.target.value)} required={enabled} placeholder="Desativado" /></div>}<button className="btn small primary" disabled={busy}>Salvar regra</button></form>;
}

function MonitorDialog({ item, status, setStatus, note, setNote, reason, setReason, busy, onClose, onSave }: { item: Row; status: string; setStatus: (value: string) => void; note: string; setNote: (value: string) => void; reason: string; setReason: (value: string) => void; busy: boolean; onClose: () => void; onSave: () => void }) {
  return <div className="modal-backdrop" role="presentation"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="monitor-title"><div className="panel-head"><h2 id="monitor-title">Atualizar ocorrência</h2><button className="btn small" onClick={onClose}>Fechar</button></div><p>{item.description}</p><div className="field"><label>Status</label><select value={status} onChange={event => setStatus(event.target.value)}>{["NOVO", "EM_ACOMPANHAMENTO", "PENDENTE", "RESOLVIDO", "DESCARTADO"].map(value => <option key={value}>{value}</option>)}</select></div><div className="field" style={{ marginTop: 12 }}><label>Observação</label><textarea value={note} onChange={event => setNote(event.target.value)} /></div><div className="field" style={{ marginTop: 12 }}><label>Justificativa para resolver/descartar</label><input value={reason} onChange={event => setReason(event.target.value)} /></div><div className="form-actions"><button className="btn" onClick={onClose}>Cancelar</button><button className="btn primary" disabled={busy} onClick={onSave}>Salvar</button></div></section></div>;
}

function SummaryPanel({ children, summaries, user, selected, onSelect, onGenerate, onValidate, busy }: { children: Row[]; summaries: Row[]; user: User; selected: Row | null; onSelect: (item: Row | null) => void; onGenerate: (child: Row) => void; onValidate: (summary: Row) => void; busy: boolean }) {
  const [childKey, setChildKey] = useState("");
  const child = children.find(item => `${item.source_system}:${item.external_id}` === childKey);
  const visible = selected ? [selected] : summaries;
  return <section className="panel"><div className="filters"><div className="field grow"><label>Criança</label><select value={childKey} onChange={event => setChildKey(event.target.value)}><option value="">Selecione uma criança</option>{children.map(item => <option key={`${item.source_system}:${item.external_id}`} value={`${item.source_system}:${item.external_id}`}>{item.projections?.nascimento?.data?.nome || item.external_id} · {item.external_id}</option>)}</select></div><button className="btn primary" disabled={!child || busy} onClick={() => child && onGenerate(child)}><FileText size={14} />Gerar rascunho</button></div>{selected && <button className="btn small" onClick={() => onSelect(null)}>Ver todos os resumos</button>}{visible.length ? visible.map(summary => <article className="summary-row" key={summary.document_id}><div><div className="panel-head"><h3>{summary.child_external_id}</h3><span className={`badge ${statusClass(summary.status)}`}>{summary.status}</span></div><div className="panel-caption">{summary.document_id} · Gerado {formatDate(summary.generated_at)}</div>{summary.missing_fields?.length > 0 && <div className="notice warning">Sem informação: {summary.missing_fields.join(", ")}</div>}<pre className="json-panel">{JSON.stringify(summary.sections, null, 2)}</pre><div className="actions" style={{ marginTop: 10 }}><a className="btn small" href={`/api/v1/resumos-alta/${encodeURIComponent(summary.document_id)}/pdf`}>Baixar PDF</a>{user.role === "PROFISSIONAL" && summary.status !== "VALIDADO" && <button className="btn small primary" onClick={() => onValidate(summary)}>Validar</button>}</div></div></article>) : <Empty>Sem resumos. Gere um rascunho a partir dos eventos de origem recebidos.</Empty>}</section>;
}

function IntegrationPanel({ events }: { events: Row[] }) {
  const example = JSON.stringify({ event_id: "evt-001", source_system: "sistema_relacional", schema_version: "1.0", event_type: "alta_maternidade", entity_type: "crianca", entity_external_id: "CRI-001", child_external_id: "CRI-001", unit_external_id: "UBS-001", occurred_at: "2026-11-20T14:30:00-03:00", data: { data_alta: "2026-11-20" } }, null, 2);
  return <section className="panel"><div className="panel-head"><h2>Recebimento de eventos</h2><span className="badge green">{events.length} eventos</span></div><div className="notice">A origem relacional envia eventos JSON por HTTPS. Esta aplicação não abre conexão com SQL Server; os campos são adaptados em `api/services.py`.</div><pre className="json-panel">{`POST /api/v1/integracao/registros\nX-API-Key: <chave configurada separadamente>\nContent-Type: application/json\n\n${example}`}</pre><div className="panel-head" style={{ marginTop: 18 }}><h3>Últimos eventos</h3></div>{events.length ? <RowsTable rows={events.slice(0, 100)} columns={[["event_type","Tipo"],["event_id","Evento"],["child_external_id","Criança"],["processing_status","Processamento"],["occurred_at","Ocorrido em"]]} /> : <Empty>Aguardando eventos enviados pela origem.</Empty>}</section>;
}

function UserAdminPanel({ onCreated }: { onCreated: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("PROFISSIONAL");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await api("/api/v1/usuarios", { method: "POST", body: JSON.stringify({ username, password, role }) });
      setUsername("");
      setPassword("");
      setMessage("Usuário criado.");
      onCreated();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Falha ao criar usuário.");
    } finally {
      setBusy(false);
    }
  }
  return <section className="panel"><div className="panel-head"><h2>Adicionar usuário</h2><span className="panel-caption">A senha é armazenada com hash.</span></div><form onSubmit={submit}><div className="form-grid"><div className="field"><label htmlFor="new-user">Usuário</label><input id="new-user" minLength={3} value={username} onChange={event => setUsername(event.target.value)} required /></div><div className="field"><label htmlFor="new-user-password">Senha temporária</label><input id="new-user-password" type="password" minLength={12} value={password} onChange={event => setPassword(event.target.value)} required /></div><div className="field"><label htmlFor="new-user-role">Perfil</label><select id="new-user-role" value={role} onChange={event => setRole(event.target.value)}><option value="PROFISSIONAL">Profissional</option><option value="LEITURA">Leitura</option></select></div></div><div className="form-actions"><button className="btn primary" disabled={busy}>{busy ? "Salvando…" : "Criar usuário"}</button></div>{message && <div className="notice">{message}</div>}</form></section>;
}
