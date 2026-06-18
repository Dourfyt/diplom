import { clearSession, getAccessToken } from "./auth";

/** Базовый URL API: пусто = тот же хост (nginx/vite проксируют на платформу) */
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const API = `${API_BASE}/api/v1`;

export class ApiAuthError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiAuthError";
  }
}

export interface ProductionLine {
  id: number;
  code: string;
  name: string;
  line_type: string;
  capacity_t_per_hour: number;
  is_available: boolean;
}

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
  organization_name?: string | null;
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
  const token = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearSession();
    throw new ApiAuthError("Сессия истекла. Войдите снова.", 401);
  }
  if (res.status === 403) {
    let detail = "Недостаточно прав";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new ApiAuthError(detail, 403);
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

export const api = {
  lines: () => request<ProductionLine[]>("/lines"),
  batches: () => request<Batch[]>("/batches"),
  plans: (view: "active" | "all" = "active") =>
    request<Plan[]>(`/plans?view=${view}`),
  kpi: (planId?: number) =>
    request<Kpi>(planId ? `/dashboard/kpi?plan_id=${planId}` : "/dashboard/kpi"),
  notifications: () => request<Notification[]>("/notifications"),
  buildPlan: (body: {
    name: string;
    horizon_hours: number;
    batch_ids?: number[] | null;
  }) =>
    request<PlanActionResult>("/plans/build", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  approvePlan: (id: number) =>
    request<PlanActionResult>(`/plans/${id}/approve`, { method: "POST" }),
  replan: (
    id: number,
    line_code: string,
    duration_hours: number,
    reason = "Аварийная остановка"
  ) =>
    request<PlanActionResult>(`/plans/${id}/replan`, {
      method: "POST",
      body: JSON.stringify({ line_code, duration_hours, reason }),
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
  checkNotifications: (planId?: number) =>
    request<{ created: number }>(
      planId ? `/notifications/check?plan_id=${planId}` : "/notifications/check",
      { method: "POST" }
    ),
};
