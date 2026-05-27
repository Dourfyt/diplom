import { getSiblingModules, ModuleId } from "../modules";

type Props = {
  current: ModuleId;
  variant?: "sidebar" | "topbar";
};

export function ModuleNav({ current, variant = "sidebar" }: Props) {
  const modules = getSiblingModules(current);

  return (
    <nav
      className={`module-nav module-nav-${variant}`}
      data-tour="module-nav"
      aria-label="Переход между модулями комплекса"
    >
      <div className="module-nav-label">Модули комплекса</div>
      <div className="module-nav-links">
        {modules.map((m) =>
          m.current ? (
            <span key={m.id} className="module-nav-btn current" aria-current="page">
              {m.label}
            </span>
          ) : (
            <a
              key={m.id}
              className="module-nav-btn"
              href={m.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {m.label}
            </a>
          )
        )}
      </div>
    </nav>
  );
}
