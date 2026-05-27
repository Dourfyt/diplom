import { useEffect, useRef, useState } from "react";
import { Plan } from "../api";
import { formatHours } from "../format";
import { StatusBadge } from "./StatusBadge";
import { IconChevron } from "./Icons";

export function PlanPicker({
  plans,
  selectedId,
  onSelect,
  showAll,
  onToggleHistory,
}: {
  plans: Plan[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  showAll: boolean;
  onToggleHistory: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = plans.find((p) => p.id === selectedId) ?? plans[0];

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  if (!selected) return null;

  return (
    <div ref={ref} className="plan-picker">
      <button
        type="button"
        className="plan-picker-trigger"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="plan-picker-label">Версия плана</span>
        <span className="plan-picker-value">
          <strong>v{selected.version_no}</strong>
          <span className="plan-picker-name">{selected.name}</span>
        </span>
        <StatusBadge status={selected.status} statusLabel={selected.status_label} />
        <IconChevron className={open ? "rotated" : ""} />
      </button>

      {open && (
        <div className="plan-picker-panel">
          <div className="plan-picker-panel-head">
            <span>Выберите версию</span>
            <button type="button" onClick={onToggleHistory}>
              {showAll ? "Скрыть архив" : "Вся история"}
            </button>
          </div>
          <ul className="plan-picker-list">
            {plans.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  className={`plan-picker-item ${p.id === selected.id ? "selected" : ""}`}
                  onClick={() => {
                    onSelect(p.id);
                    setOpen(false);
                  }}
                >
                  <div className="plan-picker-item-top">
                    <span className="plan-ver">v{p.version_no}</span>
                    <StatusBadge status={p.status} statusLabel={p.status_label} />
                    {p.is_simulation && <span className="tag-sim">симуляция</span>}
                  </div>
                  <span className="plan-picker-item-name">{p.name}</span>
                  <span className="plan-picker-item-meta">
                    #{p.id} · {formatHours(p.horizon_hours)} ч · {p.items.length} операций
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
