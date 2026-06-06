import { useEffect, useState } from "react";
import type { Batch } from "../api";
import { formatHours } from "../format";

type Props = {
  open: boolean;
  batches: Batch[];
  busy: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string; horizon_hours: number; batch_ids: number[] | null }) => void;
};

export function BuildPlanModal({ open, batches, busy, onClose, onSubmit }: Props) {
  const [name, setName] = useState("");
  const [horizon, setHorizon] = useState(8);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [allBatches, setAllBatches] = useState(true);

  useEffect(() => {
    if (open) {
      setName(`Сменный план ${new Date().toLocaleDateString("ru-RU")}`);
      setHorizon(8);
      setSelectedIds([]);
      setAllBatches(true);
    }
  }, [open]);

  if (!open) return null;

  const eligible = batches.filter((b) => b.status === "accepted" || b.status === "queued");

  const toggleBatch = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-card"
        role="dialog"
        aria-labelledby="build-plan-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h2 id="build-plan-title">Новый план</h2>
          <p>Параметры передаются в API платформы (`POST /plans/build`)</p>
        </div>
        <div className="modal-body">
          <label className="field">
            <span>Название</span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={busy}
            />
          </label>
          <label className="field">
            <span>Горизонт, ч (1–168)</span>
            <input
              type="number"
              min={1}
              max={168}
              step={0.5}
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
              disabled={busy}
            />
          </label>
          <fieldset className="field">
            <legend>Партии из учёта</legend>
            <label className="checkbox-row">
              <input
                type="radio"
                checked={allBatches}
                onChange={() => setAllBatches(true)}
                disabled={busy}
              />
              Все доступные в очереди ({eligible.length})
            </label>
            <label className="checkbox-row">
              <input
                type="radio"
                checked={!allBatches}
                onChange={() => setAllBatches(false)}
                disabled={busy}
              />
              Выбрать вручную
            </label>
            {!allBatches && (
              <div className="batch-pick-list">
                {eligible.length === 0 ? (
                  <p className="hint">Нет партий со статусом «принята» / «в очереди»</p>
                ) : (
                  eligible.map((b) => (
                    <label key={b.id} className="checkbox-row">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(b.id)}
                        onChange={() => toggleBatch(b.id)}
                        disabled={busy}
                      />
                      <span className="mono">{b.code}</span>
                      <span>{b.name}</span>
                      <span className="hint">{(b.priority_score ?? 0).toFixed(1)}</span>
                    </label>
                  ))
                )}
              </div>
            )}
          </fieldset>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={busy}>
            Отмена
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={
              busy ||
              !name.trim() ||
              horizon < 1 ||
              horizon > 168 ||
              (!allBatches && selectedIds.length === 0)
            }
            onClick={() =>
              onSubmit({
                name: name.trim(),
                horizon_hours: horizon,
                batch_ids: allBatches ? null : selectedIds,
              })
            }
          >
            Построить · {formatHours(horizon)} ч
          </button>
        </div>
      </div>
    </div>
  );
}
