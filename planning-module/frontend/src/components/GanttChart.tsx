import { Plan } from "../api";

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

const LINE_META: Record<string, { label: string; color: string }> = {
  L1: { label: "Сушка / сепарация", color: "var(--line-l1)" },
  L2: { label: "Термообезвреживание", color: "var(--line-l2)" },
};

export function GanttChart({ plan }: { plan: Plan }) {
  if (!plan.items.length) {
    return (
      <div className="empty-state compact">
        <p>Нет операций в плане</p>
        <span>Постройте расписание или выберите другую версию плана</span>
      </div>
    );
  }

  const starts = plan.items.map((i) => new Date(i.start_at).getTime());
  const ends = plan.items.map((i) => new Date(i.end_at).getTime());
  const t0 = Math.min(...starts);
  const t1 = Math.max(...ends);
  const span = t1 - t0 || 1;

  const ticks = 5;
  const timeLabels = Array.from({ length: ticks }, (_, i) => {
    const t = t0 + (span / (ticks - 1)) * i;
    return new Date(t);
  });

  const byLine = plan.items.reduce<Record<string, typeof plan.items>>((acc, item) => {
    (acc[item.line_code] ||= []).push(item);
    return acc;
  }, {});

  return (
    <div className="gantt-wrap">
      <div className="gantt-axis">
        <div className="gantt-axis-label" />
        <div className="gantt-axis-track">
          {timeLabels.map((d, i) => (
            <span key={i} style={{ left: `${(i / (ticks - 1)) * 100}%` }}>
              {formatTime(d.toISOString())}
            </span>
          ))}
        </div>
      </div>

      {Object.entries(byLine).map(([line, items]) => {
        const meta = LINE_META[line] ?? { label: line, color: "var(--brand)" };
        return (
          <div key={line} className="gantt-row">
            <div className="gantt-line-label">
              <span className="line-code" style={{ background: meta.color }}>
                {line}
              </span>
              <span className="line-name">{meta.label}</span>
            </div>
            <div className="gantt-track">
              {items.map((item) => {
                const left = ((new Date(item.start_at).getTime() - t0) / span) * 100;
                const width = Math.max(
                  6,
                  ((new Date(item.end_at).getTime() - new Date(item.start_at).getTime()) / span) *
                    100
                );
                return (
                  <div
                    key={item.id}
                    className="gantt-bar"
                    style={{
                      left: `${left}%`,
                      width: `${width}%`,
                      background: meta.color,
                    }}
                    title={`${item.batch_code}\n${formatTime(item.start_at)} — ${formatTime(item.end_at)}\nВыход: ${item.planned_output_tons} т`}
                  >
                    <span className="gantt-bar-code">{item.batch_code}</span>
                    <span className="gantt-bar-time">
                      {formatTime(item.start_at)}–{formatTime(item.end_at)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      <div className="gantt-legend">
        {Object.entries(LINE_META).map(([code, m]) => (
          <span key={code}>
            <i style={{ background: m.color }} />
            {code} — {m.label}
          </span>
        ))}
      </div>
    </div>
  );
}
