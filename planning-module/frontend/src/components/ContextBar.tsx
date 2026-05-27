import { Plan } from "../api";
import { formatHours } from "../format";
import { StatusBadge } from "./StatusBadge";

export function ContextBar({
  plan,
  approvedPlan,
}: {
  plan: Plan | undefined;
  approvedPlan: Plan | undefined;
}) {
  if (!plan) return null;

  const isWorking =
    approvedPlan &&
    !plan.is_simulation &&
    plan.id === approvedPlan.id;

  return (
    <div className="context-bar" data-tour="context-bar">
      <div className="context-bar-inner">
        <div className="context-chip">
          <span className="context-chip-label">Просмотр</span>
          <strong>
            v{plan.version_no} · {plan.name}
          </strong>
          <StatusBadge status={plan.status} statusLabel={plan.status_label} />
          {plan.is_simulation && <span className="tag-sim">симуляция</span>}
        </div>
        {approvedPlan && (
          <div className="context-chip context-chip-muted">
            <span className="context-chip-label">В производстве</span>
            <strong>v{approvedPlan.version_no}</strong>
            {isWorking ? (
              <span className="tag-live">активный</span>
            ) : (
              <StatusBadge
                status={approvedPlan.status}
                statusLabel={approvedPlan.status_label}
              />
            )}
          </div>
        )}
        <div className="context-chip context-chip-muted">
          <span className="context-chip-label">Горизонт</span>
          <strong>{formatHours(plan.horizon_hours)} ч</strong>
          <span className="context-meta">{plan.items.length} операций</span>
        </div>
      </div>
    </div>
  );
}
