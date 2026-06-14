export type ModuleId = "api" | "planning" | "eco";

export type SiblingModule = {
  id: ModuleId;
  label: string;
  url: string;
  current: boolean;
};

function hostBase(): string {
  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}`;
  }
  return "http://runcourse.online";
}

function moduleUrl(envValue: string | undefined, port: number): string {
  if (envValue?.trim()) return envValue.trim().replace(/\/$/, "");
  return `${hostBase()}:${port}`;
}

export function getSiblingModules(current: ModuleId): SiblingModule[] {
  const api = moduleUrl(import.meta.env.VITE_MODULE_API_URL, 8080);
  const planning = moduleUrl(import.meta.env.VITE_MODULE_PLANNING_URL, 5173);
  const eco = moduleUrl(import.meta.env.VITE_MODULE_ECO_URL, 8001);

  const items: Omit<SiblingModule, "current">[] = [
    { id: "api", label: "API платформы", url: `${api}/docs` },
    { id: "planning", label: "Планирование", url: planning },
    { id: "eco", label: "Отчётность", url: eco },
  ];

  return items.map((item) => ({ ...item, current: item.id === current }));
}
