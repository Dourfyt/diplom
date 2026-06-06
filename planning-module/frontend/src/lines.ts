export const LINE_META: Record<
  string,
  { label: string; color: string; rowClass: string; badgeClass: string }
> = {
  L1: {
    label: "Сушка / сепарация",
    color: "var(--line-l1)",
    rowClass: "schedule-row-l1",
    badgeClass: "badge-line-l1",
  },
  L2: {
    label: "Термообезвреживание",
    color: "var(--line-l2)",
    rowClass: "schedule-row-l2",
    badgeClass: "badge-line-l2",
  },
};

export function getLineMeta(lineCode: string) {
  return (
    LINE_META[lineCode] ?? {
      label: lineCode,
      color: "var(--brand)",
      rowClass: "",
      badgeClass: "badge-neutral",
    }
  );
}
