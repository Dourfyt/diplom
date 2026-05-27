import { ReactNode } from "react";

export function KpiCard({
  label,
  value,
  hint,
  accent,
  icon,
  trend,
}: {
  label: string;
  value: string | number;
  hint?: string;
  accent: string;
  icon: ReactNode;
  trend?: "up" | "down" | "neutral";
}) {
  return (
    <article className="kpi-card-v2" style={{ "--kpi-accent": accent } as React.CSSProperties}>
      <div className="kpi-card-v2-icon">{icon}</div>
      <div className="kpi-card-v2-body">
        <span className="kpi-card-v2-label">{label}</span>
        <div className="kpi-card-v2-value-row">
          <span className="kpi-card-v2-value">{value}</span>
          {trend && trend !== "neutral" && (
            <span className={`kpi-trend kpi-trend-${trend}`}>{trend === "up" ? "↑" : "↓"}</span>
          )}
        </div>
        {hint && <span className="kpi-card-v2-hint">{hint}</span>}
      </div>
    </article>
  );
}
