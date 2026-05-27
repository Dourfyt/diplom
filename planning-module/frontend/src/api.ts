/** Базовый URL API: пусто = тот же хост (nginx/vite проксируют на платформу) */
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const API = `${API_BASE}/api/v1`;

export interface Batch {
  id: number;
  code: string;
  name: string;
  fkko_code: string;
  hazard_class: number;
  volume_tons: number;
  storage_deadline_hours: number;
  priority_score: number | null;
  storage_risk_hours: number | null;
  route_codes: string;
  status: string;
  processed_tons?: number | null;
  disposed_tons?: number | null;
  remaining_tons?: number | null;
}

export interface ScheduleItem {
  id: number;
  batch_code: string;
  line_code: string;
  operation_code: string;
  start_at: string;
  end_at: string;
  priority_score: number;
  planned_output_tons: number;
  planned_loss_tons: number;
}

export interface Plan {
  id: number;
  name: string;
  horizon_hours: number;
  status: string;
  status_label: string;
  version_no: number;
  is_simulation: boolean;
  parent_plan_id: number | null;
  items: ScheduleItem[];
}

export interface PlanActionResult {
  plan: Plan;
  message: string;
}

export interface Kpi {
  plan_id: number | null;
  total_batches: number;
  scheduled_batches: number;
  line_utilization: Record<string, number>;
  total_idle_hours: number;
  batches_at_storage_risk: number;
  avg_priority: number;
  notifications_new: number;
  oee_percent: number;
  plan_completion_percent: number;
}

export interface Notification {
  id: number;
  trigger_code: string;
  title: string;
  message: string;
  status: string;
  created_at: string;
}

export interface SimCompare {
  base_plan_id: number;
  sim_plan_id: number;
  kpi_base: Kpi;
  kpi_sim: Kpi;
  differences: Record<string, number>;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

export const api = {
  batches: () => request<Batch[]>("/batches"),
  plans: (view: "active" | "all" = "active") =>
    request<Plan[]>(`/plans?view=${view}`),
  plan: (id: number) => request<Plan>(`/plans/${id}`),
  kpi: (planId?: number) =>
    request<Kpi>(planId ? `/dashboard/kpi?plan_id=${planId}` : "/dashboard/kpi"),
  notifications: () => request<Notification[]>("/notifications"),
  buildPlan: (body: { name: string; horizon_hours: number }) =>
    request<PlanActionResult>("/plans/build", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  approvePlan: (id: number) =>
    request<PlanActionResult>(`/plans/${id}/approve`, { method: "POST" }),
  replan: (id: number, line_code: string, duration_hours: number) =>
    request<PlanActionResult>(`/plans/${id}/replan`, {
      method: "POST",
      body: JSON.stringify({ line_code, duration_hours, reason: "Аварийная остановка" }),
    }),
  simulate: (base_plan_id: number, scenario: string, line_downtime?: Record<string, number>) =>
    request<SimCompare>("/simulations", {
      method: "POST",
      body: JSON.stringify({
        base_plan_id,
        name: `Симуляция ${scenario}`,
        scenario,
        line_downtime,
      }),
    }),
  ackNotification: (id: number) =>
    request<{ ok: boolean }>(`/notifications/${id}/ack`, { method: "PATCH" }),
};
