import { useEffect, useState } from "react";
import type { ProductionLine } from "../api";
import { formatHours } from "../format";

type Props = {
  open: boolean;
  lines: ProductionLine[];
  busy: boolean;
  onClose: () => void;
  onSubmit: (data: { line_code: string; duration_hours: number; reason: string }) => void;
};

export function ReplanModal({ open, lines, busy, onClose, onSubmit }: Props) {
  const [lineCode, setLineCode] = useState("");
  const [duration, setDuration] = useState(8);
  const [reason, setReason] = useState("Аварийная остановка");

  useEffect(() => {
    if (open && lines.length) {
      const preferred = lines.find((l) => l.code === "L2") ?? lines[0];
      setLineCode(preferred.code);
      setDuration(8);
      setReason("Аварийная остановка");
    }
  }, [open, lines]);

  if (!open) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-card"
        role="dialog"
        aria-labelledby="replan-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h2 id="replan-title">Перепланирование после простоя</h2>
          <p>
            Линии из справочника платформы. Горизонт плана увеличится на время простоя,
            чтобы операции на обеих линиях остались в расписании.
          </p>
        </div>
        <div className="modal-body">
          <label className="field">
            <span>Линия</span>
            <select
              value={lineCode}
              onChange={(e) => setLineCode(e.target.value)}
              disabled={busy || lines.length === 0}
            >
              {lines.map((line) => (
                <option key={line.id} value={line.code}>
                  {line.code} — {line.name}
                  {!line.is_available ? " (недоступна)" : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Длительность простоя, ч (0,5–72)</span>
            <input
              type="number"
              min={0.5}
              max={72}
              step={0.5}
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              disabled={busy}
            />
          </label>
          <label className="field">
            <span>Причина</span>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={busy}
            />
          </label>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={busy}>
            Отмена
          </button>
          <button
            type="button"
            className="btn btn-danger-soft"
            disabled={
              busy ||
              !lineCode ||
              duration < 0.5 ||
              duration > 72 ||
              !reason.trim() ||
              lines.length === 0
            }
            onClick={() =>
              onSubmit({
                line_code: lineCode,
                duration_hours: duration,
                reason: reason.trim(),
              })
            }
          >
            Перепланировать · {formatHours(duration)} ч
          </button>
        </div>
      </div>
    </div>
  );
}
