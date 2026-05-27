import { planStatusClass, planStatusLabel } from "../labels";

export function StatusBadge({
  status,
  statusLabel,
}: {
  status: string;
  statusLabel?: string;
}) {
  return (
    <span className={`status-badge status-${planStatusClass(status)}`}>
      <i className="status-dot" />
      {planStatusLabel(status, statusLabel)}
    </span>
  );
}
