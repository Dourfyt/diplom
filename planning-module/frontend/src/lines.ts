import type { CSSProperties } from "react";
import type { ProductionLine } from "./api";

/** Палитра UI — единственное, чего нет в API линий */
const LINE_COLORS = ["var(--line-l1)", "var(--line-l2)", "var(--brand)", "var(--warn)"];

export type LineMeta = {
  code: string;
  label: string;
  color: string;
  capacity?: number;
  isAvailable: boolean;
};

export function buildLineMetaMap(lines: ProductionLine[]): Record<string, LineMeta> {
  return Object.fromEntries(
    lines.map((line, index) => [
      line.code,
      {
        code: line.code,
        label: line.name?.trim() || line.line_type?.trim() || line.code,
        color: LINE_COLORS[index % LINE_COLORS.length],
        capacity: line.capacity_t_per_hour,
        isAvailable: line.is_available,
      },
    ])
  );
}

export function getLineMeta(
  map: Record<string, LineMeta>,
  lineCode: string
): LineMeta {
  return (
    map[lineCode] ?? {
      code: lineCode,
      label: lineCode,
      color: "var(--brand)",
      isAvailable: true,
    }
  );
}

export function lineRowStyle(color: string): CSSProperties {
  return {
    ["--row-line-color" as string]: color,
  };
}

export function lineBadgeStyle(color: string): CSSProperties {
  return {
    ["--badge-line-color" as string]: color,
  };
}
