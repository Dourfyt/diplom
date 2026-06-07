import { FormEvent, useState } from "react";
import { login } from "../auth";
import { IconLeaf } from "./Icons";

interface LoginPageProps {
  onSuccess: () => void;
}

export function LoginPage({ onSuccess }: LoginPageProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка входа");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <div className="brand-icon">
            <IconLeaf />
          </div>
          <div>
            <strong>ЭкоПлан</strong>
            <span>Планирование переработки отходов</span>
          </div>
        </div>

        <h1>Вход в систему</h1>
        <p className="login-lead">Используйте учётную запись платформы комплекса</p>

        {error && <div className="alert alert-error login-alert">{error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <label className="login-field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="chief@eco.local"
              required
              autoFocus
              autoComplete="username"
            />
          </label>
          <label className="login-field">
            <span>Пароль</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          <button type="submit" className="btn btn-primary login-submit" disabled={busy}>
            {busy ? "Вход…" : "Войти"}
          </button>
        </form>

        <p className="login-hint">
          Демо: <code>chief@eco.local</code> / <code>chief123</code>
        </p>
      </div>
    </div>
  );
}
