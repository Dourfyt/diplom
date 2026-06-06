import { useCallback, useEffect, useRef, useState } from "react";
import {
  isPlanningTourActive,
  startPlanningTour,
  stopPlanningTour,
  type PlanningTab,
} from "./training/planningTour";
import { api, Batch, Kpi, Notification, Plan, SimCompare } from "./api";
import { formatHours, formatNumber } from "./format";
import { notificationStatusLabel, planStatusLabel } from "./labels";
import { ContextBar } from "./components/ContextBar";
import { ModuleNav } from "./components/ModuleNav";
import { GanttChart } from "./components/GanttChart";
import { KpiCard } from "./components/KpiCard";
import { PlanPicker } from "./components/PlanPicker";
import {
  IconAlert,
  IconBell,
  IconCalendar,
  IconChart,
  IconDashboard,
  IconFlask,
  IconLeaf,
  IconPackage,
  IconPlus,
  IconRefresh,
  IconSearch,
  IconZap,
} from "./components/Icons";
import { StatusBadge } from "./components/StatusBadge";
import { getLineMeta } from "./lines";

type Tab = PlanningTab;

const NAV: { id: Tab; label: string; Icon: typeof IconDashboard }[] = [
  { id: "dashboard", label: "Обзор", Icon: IconDashboard },
  { id: "schedule", label: "Расписание", Icon: IconCalendar },
  { id: "batches", label: "Партии", Icon: IconPackage },
  { id: "simulation", label: "Симуляция", Icon: IconFlask },
  { id: "notifications", label: "Уведомления", Icon: IconBell },
];

const PAGE_TITLES: Record<Tab, { title: string; subtitle: string }> = {
  dashboard: { title: "Обзор производства", subtitle: "Ключевые показатели и загрузка линий" },
  schedule: { title: "Расписание переработки", subtitle: "Gantt-диаграмма и операции плана" },
  batches: { title: "Партии отходов", subtitle: "Очередь на переработку с приоритетами" },
  simulation: { title: "Сценарное моделирование", subtitle: "Сравнение вариантов «что если»" },
  notifications: { title: "Центр уведомлений", subtitle: "Риски простоев и просрочки хранения" },
};

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function HazardClass({ n }: { n: number }) {
  const cls = n <= 3 ? "hazard-3" : n === 4 ? "hazard-4" : "hazard-5";
  return <span className={`hazard ${cls}`}>{n}</span>;
}

function DeltaCell({ value }: { value: number }) {
  if (value === 0) return <span>0</span>;
  const better = value < 0;
  const text = formatNumber(value, 2).replace(/\.?0+$/, "");
  return (
    <span className={better ? "delta-negative" : "delta-positive"}>
      {value > 0 ? "+" : ""}
      {text}
    </span>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [kpi, setKpi] = useState<Kpi | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [simResult, setSimResult] = useState<SimCompare | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [showAllPlans, setShowAllPlans] = useState(false);
  const [batchQuery, setBatchQuery] = useState("");
  const [tourActive, setTourActive] = useState(false);
  const tourActiveRef = useRef(false);

  const selectedPlan = plans.find((p) => p.id === selectedPlanId) ?? plans[0];
  const approvedPlan = plans.find(
    (p) => !p.is_simulation && (p.status === "approved" || p.status === "published")
  );
  const page = PAGE_TITLES[tab];
  const newNotifCount = notifications.filter((n) => n.status === "new").length;
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [b, p, n] = await Promise.all([
        api.batches(),
        api.plans(showAllPlans ? "all" : "active"),
        api.notifications(),
      ]);
      setBatches(b);
      setPlans(p);
      setNotifications(n);
      const pid = selectedPlanId ?? p[0]?.id;
      if (pid) {
        setSelectedPlanId(pid);
        setKpi(await api.kpi(pid));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки данных");
    } finally {
      setLoading(false);
    }
  }, [selectedPlanId, showAllPlans]);

  useEffect(() => {
    load();
  }, [showAllPlans]);

  useEffect(() => {
    if (selectedPlanId) {
      api.kpi(selectedPlanId).then(setKpi).catch(() => {});
    }
  }, [selectedPlanId, plans]);

  const handleTrainingToggle = () => {
    if (tourActiveRef.current || isPlanningTourActive()) {
      stopPlanningTour();
      tourActiveRef.current = false;
      setTourActive(false);
      return;
    }
    startPlanningTour({
      tab,
      setTab,
      onStart: () => {
        tourActiveRef.current = true;
        setTourActive(true);
      },
      onEnd: () => {
        tourActiveRef.current = false;
        setTourActive(false);
      },
    });
  };

  const handleBuild = async () => {
    setBusy(true);
    try {
      const result = await api.buildPlan({
        name: `Сменный план ${new Date().toLocaleDateString("ru-RU")}`,
        horizon_hours: 8,
      });
      setToast(result.message);
      await load();
      setSelectedPlanId(result.plan.id);
      setTab("schedule");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  };

  const handleApprove = async () => {
    if (!selectedPlan || selectedPlan.is_simulation) return;
    setBusy(true);
    try {
      const result = await api.approvePlan(selectedPlan.id);
      setToast(result.message);
      await load();
      setSelectedPlanId(result.plan.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  };

  const handleReplan = async () => {
    if (!selectedPlan) return;
    setBusy(true);
    try {
      const result = await api.replan(selectedPlan.id, "L2", 8);
      setToast(result.message);
      await load();
      setSelectedPlanId(result.plan.id);
      setTab("schedule");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  };

  const handleSimulate = async (scenario: string) => {
    if (!selectedPlan) return;
    setBusy(true);
    try {
      const result = await api.simulate(
        selectedPlan.id,
        scenario,
        scenario === "emergency" ? { L2: 8 } : undefined
      );
      setSimResult(result);
      await load();
      setSelectedPlanId(result.sim_plan_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  };

  const filteredBatches = batches
    .filter(
      (b) =>
        !batchQuery.trim() ||
        b.code.toLowerCase().includes(batchQuery.toLowerCase()) ||
        b.name.toLowerCase().includes(batchQuery.toLowerCase())
    )
    .sort((a, b) => (b.priority_score ?? 0) - (a.priority_score ?? 0));

  if (loading && !plans.length) {
    return (
      <div className="loading-screen">
        <div className="brand-loading">
          <div className="brand-icon">
            <IconLeaf />
          </div>
          <strong>ЭкоПлан</strong>
        </div>
        <div className="spinner" />
        <p>Загрузка модуля планирования…</p>
      </div>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-icon">
            <IconLeaf />
          </div>
          <div className="brand-text">
            <strong>ЭкоПлан</strong>
            <span>Планирование переработки отходов</span>
          </div>
        </div>

        <ModuleNav current="planning" variant="sidebar" />

        <nav className="sidebar-nav" data-tour="sidebar-nav">
          {NAV.map(({ id, label, Icon }) => (
            <button
              key={id}
              type="button"
              className={`nav-item ${tab === id ? "active" : ""}`}
              data-tour={`nav-${id}`}
              onClick={() => setTab(id)}
            >
              <Icon size={20} />
              {label}
              {id === "notifications" && newNotifCount > 0 && (
                <span className="badge-count">{newNotifCount}</span>
              )}
            </button>
          ))}
        </nav>

        {kpi && (
          <div className="sidebar-footer">
            <div>Рабочий план</div>
            <div className="mini-stat">
              <span>{approvedPlan ? `вер. ${approvedPlan.version_no}` : "не утверждён"}</span>
              <span>
                {approvedPlan
                  ? planStatusLabel(approvedPlan.status, approvedPlan.status_label)
                  : "—"}
              </span>
            </div>
            <div className="mini-stat">
              <span>OEE</span>
              <span>{kpi.oee_percent}%</span>
            </div>
          </div>
        )}
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar-left" data-tour="topbar-title">
            <h1>{page.title}</h1>
            <p>{page.subtitle}</p>
          </div>
          <div className="topbar-actions">
            <ModuleNav current="planning" variant="topbar" />
            <button
              type="button"
              className={`btn ${tourActive ? "btn-primary" : "btn-ghost"}`}
              onClick={handleTrainingToggle}
              disabled={loading}
              data-tour="btn-training"
            >
              <IconZap />
              {tourActive ? "Тур…" : "Обучение"}
            </button>
            <div data-tour="plan-picker">
              {plans.length > 0 && (
                <PlanPicker
                  plans={plans}
                  selectedId={selectedPlanId}
                  onSelect={setSelectedPlanId}
                  showAll={showAllPlans}
                  onToggleHistory={() => setShowAllPlans((v) => !v)}
                />
              )}
            </div>
            <button type="button" className="btn btn-ghost" onClick={load} disabled={busy}>
              <IconRefresh />
              Обновить
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleBuild}
              disabled={busy}
              data-tour="btn-new-plan"
            >
              <IconPlus />
              Новый план
            </button>
          </div>
        </header>

        <ContextBar plan={selectedPlan} approvedPlan={approvedPlan} />

        <main className="content">
          {toast && (
            <div className="toast">
              <span>{toast}</span>
              <button type="button" onClick={() => setToast(null)} aria-label="Закрыть">
                ×
              </button>
            </div>
          )}

          {error && (
            <div className="alert alert-error">
              <span>{error}</span>
              <button type="button" onClick={() => setError(null)} aria-label="Закрыть">
                ×
              </button>
            </div>
          )}

          {tab === "dashboard" && kpi && (
            <div className="page-section">
              <div className="kpi-grid">
                <div data-tour="kpi-oee">
                <KpiCard
                  label="OEE оборудования"
                  value={`${kpi.oee_percent}%`}
                  hint="общая эффективность линий"
                  accent="var(--brand)"
                  icon={<IconChart />}
                />
                </div>
                <div data-tour="kpi-completion">
                <KpiCard
                  label="Выполнение плана"
                  value={`${kpi.plan_completion_percent}%`}
                  hint={`${kpi.scheduled_batches} из ${kpi.total_batches} партий`}
                  accent="var(--line-l2)"
                  icon={<IconZap />}
                />
                </div>
                <div data-tour="kpi-idle">
                <KpiCard
                  label="Суммарный простой"
                  value={`${formatHours(kpi.total_idle_hours)} ч`}
                  accent="var(--warn)"
                  icon={<IconCalendar />}
                />
                </div>
                <div data-tour="kpi-storage">
                <KpiCard
                  label="Риск хранения"
                  value={kpi.batches_at_storage_risk}
                  hint="партий < 6 ч до срока"
                  accent="var(--danger)"
                  icon={<IconAlert />}
                  trend={kpi.batches_at_storage_risk > 0 ? "up" : "neutral"}
                />
                </div>
                <div data-tour="kpi-priority">
                <KpiCard
                  label="Средний приоритет"
                  value={formatNumber(kpi.avg_priority)}
                  accent="#6366f1"
                  icon={<IconPackage />}
                />
                </div>
                <div data-tour="kpi-notifications">
                <KpiCard
                  label="Уведомления"
                  value={kpi.notifications_new}
                  hint="требуют внимания"
                  accent="var(--info)"
                  icon={<IconBell />}
                />
                </div>
              </div>

              <div className="quick-actions" data-tour="quick-actions">
                <button type="button" className="quick-action" onClick={() => setTab("schedule")}>
                  <IconCalendar />
                  <span>Расписание</span>
                </button>
                <button type="button" className="quick-action" onClick={() => setTab("batches")}>
                  <IconPackage />
                  <span>Партии</span>
                </button>
                <button type="button" className="quick-action" onClick={() => setTab("simulation")}>
                  <IconFlask />
                  <span>Симуляция</span>
                </button>
                <button
                  type="button"
                  className="quick-action quick-action-accent"
                  onClick={handleBuild}
                  disabled={busy}
                >
                  <IconPlus />
                  <span>Новый план</span>
                </button>
              </div>

              <div className="card" data-tour="lines-utilization">
                <div className="card-header">
                  <div>
                    <h2>Загрузка производственных линий</h2>
                    <p>Текущий план #{selectedPlan?.id ?? "—"}</p>
                  </div>
                </div>
                <div className="card-body">
                  {Object.entries(kpi.line_utilization).map(([line, pct]) => (
                    <div key={line} className="util-bar-row">
                      <span className="line-tag" style={{ color: line === "L1" ? "var(--line-l1)" : "var(--line-l2)" }}>
                        {line}
                      </span>
                      <div className="util-bar-track">
                        <div
                          className="util-bar-fill"
                          style={{
                            width: `${Math.min(pct, 100)}%`,
                            background: line === "L1" ? "var(--line-l1)" : "var(--line-l2)",
                          }}
                        />
                      </div>
                      <span className="util-bar-pct">{pct}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {tab === "schedule" && (
            <div className="page-section" data-tour="schedule-panel">
              <div className="card">
                <div className="toolbar" data-tour="schedule-toolbar">
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    data-tour="schedule-approve"
                    disabled={
                      !selectedPlan ||
                      busy ||
                      selectedPlan.is_simulation ||
                      selectedPlan.status === "approved" ||
                      selectedPlan.status === "published"
                    }
                    onClick={handleApprove}
                  >
                    Утвердить план
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger-soft btn-sm"
                    data-tour="schedule-replan"
                    disabled={!selectedPlan || busy}
                    onClick={handleReplan}
                  >
                    Перепланировать · простой L2 (8 ч)
                  </button>
                </div>
                {selectedPlan ? (
                  <>
                    <div className="card-header" data-tour="schedule-plan-header">
                      <div>
                        <h2>{selectedPlan.name}</h2>
                        <p>
                          Версия {selectedPlan.version_no} · горизонт {formatHours(selectedPlan.horizon_hours)} ч ·{" "}
                          <StatusBadge
                            status={selectedPlan.status}
                            statusLabel={selectedPlan.status_label}
                          />
                          {selectedPlan.is_simulation && (
                            <span className="badge badge-warn" style={{ marginLeft: 6 }}>
                              симуляция
                            </span>
                          )}
                        </p>
                      </div>
                    </div>
                    <div className="card-body" data-tour="schedule-gantt">
                      <GanttChart plan={selectedPlan} />
                    </div>
                    <div className="card-body flush" data-tour="schedule-table">
                      <div className="table-wrap">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>Партия</th>
                              <th>Линия</th>
                              <th>Начало</th>
                              <th>Окончание</th>
                              <th>Выход, т</th>
                              <th>Потери, т</th>
                              <th>Приоритет</th>
                            </tr>
                          </thead>
                          <tbody>
                            {selectedPlan.items.map((i) => {
                              const lineMeta = getLineMeta(i.line_code);
                              return (
                              <tr key={i.id} className={lineMeta.rowClass || undefined}>
                                <td>
                                  <strong className="mono">{i.batch_code}</strong>
                                </td>
                                <td>
                                  <span className={`badge ${lineMeta.badgeClass}`}>{i.line_code}</span>
                                </td>
                                <td className="mono">{formatDateTime(i.start_at)}</td>
                                <td className="mono">{formatDateTime(i.end_at)}</td>
                                <td>{i.planned_output_tons}</td>
                                <td>{i.planned_loss_tons}</td>
                                <td>{i.priority_score.toFixed(1)}</td>
                              </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="empty-state">
                    <p>Нет планов</p>
                    <span>Нажмите «Новый план» для построения расписания</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {tab === "batches" && (
            <div className="card" data-tour="batches-panel">
              <div className="card-header" data-tour="batches-header">
                <div>
                  <h2>Очередь партий</h2>
                  <p>
                    Приоритет планировщика и баланс по журналу учёта (переработано / вывезено / остаток)
                  </p>
                </div>
                <span className="badge badge-neutral">{filteredBatches.length} / {batches.length}</span>
              </div>
              <div className="card-body">
                <div className="search-field" data-tour="batches-search">
                  <IconSearch />
                  <input
                    type="search"
                    placeholder="Поиск по коду или наименованию…"
                    value={batchQuery}
                    onChange={(e) => setBatchQuery(e.target.value)}
                  />
                </div>
              </div>
              <div className="card-body flush">
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th data-tour="batches-col-code">Код</th>
                        <th>Наименование</th>
                        <th>Класс</th>
                        <th data-tour="batches-col-balance">Поступило, т</th>
                        <th>Переработано, т</th>
                        <th>Вывезено, т</th>
                        <th>Остаток, т</th>
                        <th data-tour="batches-col-storage">Хранение</th>
                        <th data-tour="batches-col-priority">Приоритет</th>
                        <th data-tour="batches-col-route">Маршрут</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredBatches.length === 0 ? (
                        <tr>
                          <td colSpan={10} className="empty-row">
                            {batchQuery.trim()
                              ? `Ничего не найдено по запросу «${batchQuery}»`
                              : "Нет партий в очереди"}
                          </td>
                        </tr>
                      ) : (
                      filteredBatches.map((b) => {
                          const risk = (b.storage_risk_hours ?? 99) < 6;
                          const prio = b.priority_score ?? 0;
                          return (
                            <tr key={b.id}>
                              <td>
                                <strong className="mono">{b.code}</strong>
                              </td>
                              <td>
                                <div>{b.name}</div>
                                <div className="mono" style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
                                  {b.fkko_code}
                                </div>
                              </td>
                              <td>
                                <HazardClass n={b.hazard_class} />
                              </td>
                              <td>{formatNumber(b.volume_tons, 2)}</td>
                              <td>{formatNumber(b.processed_tons ?? 0, 2)}</td>
                              <td>{formatNumber(b.disposed_tons ?? 0, 2)}</td>
                              <td>
                                <strong>{formatNumber(b.remaining_tons ?? b.volume_tons, 2)}</strong>
                              </td>
                              <td>
                                {(b.storage_risk_hours ?? 0).toFixed(1)} ч
                                {risk && <span className="badge badge-danger" style={{ marginLeft: 6 }}>риск</span>}
                              </td>
                              <td>
                                <div className="priority-bar">
                                  <div className="bar">
                                    <i style={{ width: `${Math.min(prio, 100)}%` }} />
                                  </div>
                                  <span>{prio.toFixed(1)}</span>
                                </div>
                              </td>
                              <td className="mono">{b.route_codes.replace(/,/g, " → ")}</td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {tab === "simulation" && (
            <div className="page-section" data-tour="simulation-panel">
              <div className="card">
                <div className="card-header">
                  <div>
                    <h2>Выберите сценарий</h2>
                    <p>
                      Базовый план #{selectedPlan?.id ?? "—"} · результат сохраняется как отдельная симуляция
                    </p>
                  </div>
                </div>
                <div className="card-body">
                  <div className="scenario-grid" data-tour="simulation-scenarios">
                    <button
                      type="button"
                      className="scenario-card"
                      data-tour="simulation-baseline"
                      disabled={!selectedPlan || busy}
                      onClick={() => handleSimulate("baseline")}
                    >
                      <h3>Базовый</h3>
                      <p>Текущие мощности и горизонт плана без изменений</p>
                    </button>
                    <button
                      type="button"
                      className="scenario-card"
                      data-tour="simulation-accelerated"
                      disabled={!selectedPlan || busy}
                      onClick={() => handleSimulate("accelerated")}
                    >
                      <h3>Ускоренный</h3>
                      <p>Сокращённый горизонт (−15%) для оценки интенсификации</p>
                    </button>
                    <button
                      type="button"
                      className="scenario-card emergency"
                      data-tour="simulation-emergency"
                      disabled={!selectedPlan || busy}
                      onClick={() => handleSimulate("emergency")}
                    >
                      <h3>Аварийный</h3>
                      <p>Остановка линии L2 на 8 часов, перераспределение операций</p>
                    </button>
                  </div>
                </div>
              </div>

              {simResult && (
                <div className="card" data-tour="simulation-result">
                  <div className="card-header">
                    <div>
                      <h2>Результат сравнения</h2>
                      <p>
                        План #{simResult.base_plan_id} → симуляция #{simResult.sim_plan_id}
                      </p>
                    </div>
                  </div>
                  <div className="card-body flush">
                    <div className="table-wrap">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Показатель</th>
                            <th>Базовый</th>
                            <th>Симуляция</th>
                            <th>Изменение</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td>Простой линий, ч</td>
                            <td>{formatHours(simResult.kpi_base.total_idle_hours)}</td>
                            <td>{formatHours(simResult.kpi_sim.total_idle_hours)}</td>
                            <td>
                              <DeltaCell value={simResult.differences.idle_hours_delta} />
                            </td>
                          </tr>
                          <tr>
                            <td>Партии под риском хранения</td>
                            <td>{simResult.kpi_base.batches_at_storage_risk}</td>
                            <td>{simResult.kpi_sim.batches_at_storage_risk}</td>
                            <td>
                              <DeltaCell value={simResult.differences.storage_risk_delta} />
                            </td>
                          </tr>
                          <tr>
                            <td>OEE, %</td>
                            <td>{simResult.kpi_base.oee_percent}</td>
                            <td>{simResult.kpi_sim.oee_percent}</td>
                            <td>
                              <DeltaCell value={simResult.differences.oee_delta} />
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === "notifications" && (
            <div className="card" data-tour="notifications-panel">
              <div className="card-header" data-tour="notifications-header">
                <div>
                  <h2>Активные оповещения</h2>
                  <p>Триггеры T1 (простой) и T2 (срок хранения)</p>
                </div>
                {newNotifCount > 0 && <span className="badge badge-danger">{newNotifCount} новых</span>}
              </div>
              <div className="card-body" data-tour="notifications-list">
                {notifications.length === 0 ? (
                  <div className="empty-state compact">
                    <p>Всё в порядке</p>
                    <span>Нет активных уведомлений по текущему плану</span>
                  </div>
                ) : (
                  <div className="notif-list">
                    {notifications.map((n) => (
                      <div
                        key={n.id}
                        className={`notif-card ${n.trigger_code === "T2" ? "danger" : ""}`}
                      >
                        <span className={`badge ${n.trigger_code === "T2" ? "badge-danger" : "badge-warn"}`}>
                          {n.trigger_code}
                        </span>
                        <div className="notif-body">
                          <h3>{n.title}</h3>
                          <p>{n.message}</p>
                          {n.status === "new" && (
                            <button
                              type="button"
                              className="btn btn-ghost btn-sm"
                              style={{ marginTop: "0.5rem" }}
                              onClick={() => api.ackNotification(n.id).then(load)}
                            >
                              Подтвердить
                            </button>
                          )}
                        </div>
                        <span className="notif-time">{formatDateTime(n.created_at)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </main>
      </div>

      <nav className="mobile-nav" aria-label="Навигация">
        {NAV.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            className={tab === id ? "active" : ""}
            onClick={() => setTab(id)}
          >
            <Icon size={22} />
            {label}
          </button>
        ))}
      </nav>
    </div>
  );
}
