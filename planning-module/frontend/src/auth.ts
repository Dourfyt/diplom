const STORAGE_KEY = "planning_auth";

export interface AuthSession {
  accessToken: string;
  role: string;
  fullName: string;
  email: string;
}

export const PLANNING_VIEW_ROLES = new Set(["operator", "chief", "ecologist", "admin"]);
export const PLANNING_WRITE_ROLES = new Set(["chief", "admin"]);

export const ROLE_LABELS: Record<string, string> = {
  operator: "Оператор",
  chief: "Руководитель",
  ecologist: "Эколог",
  admin: "Администратор",
};

export function canWritePlanning(role: string): boolean {
  return PLANNING_WRITE_ROLES.has(role);
}

export function getSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as AuthSession;
    if (!data.accessToken || !data.role) return null;
    return data;
  } catch {
    return null;
  }
}

export function setSession(session: AuthSession): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function getAccessToken(): string | null {
  return getSession()?.accessToken ?? null;
}

export async function login(email: string, password: string): Promise<AuthSession> {
  const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
  });
  if (!res.ok) {
    let detail = "Неверный email или пароль";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  const data = await res.json();
  const session: AuthSession = {
    accessToken: data.access_token,
    role: data.role,
    fullName: data.full_name,
    email: email.trim().toLowerCase(),
  };
  if (!PLANNING_VIEW_ROLES.has(session.role)) {
    throw new Error("Недостаточно прав для модуля планирования");
  }
  setSession(session);
  return session;
}

export function logout(): void {
  clearSession();
}
