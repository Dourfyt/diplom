/** Подписи статусов (синхронно с waste-complex-platform/api/app/labels.py) */

export function planStatusLabel(status: string, statusLabel?: string): string {
  if (statusLabel) return statusLabel;
  const map: Record<string, string> = {
    draft: "Черновик",
    approved: "Утверждён",
    published: "Утверждён",
    archived: "В архиве",
  };
  return map[status] ?? status;
}

export function planStatusClass(status: string): string {
  if (status === "approved" || status === "published") return "approved";
  if (status === "draft") return "draft";
  if (status === "archived") return "archived";
  return "neutral";
}

export function notificationStatusLabel(status: string): string {
  const map: Record<string, string> = {
    new: "Новое",
    sent: "Отправлено",
    acknowledged: "Обработано",
  };
  return map[status] ?? status;
}

/** Статусы партий из waste_batches (модуль учёта) */
export function batchStatusLabel(status: string): string {
  const map: Record<string, string> = {
    accepted: "Принята",
    queued: "В очереди",
    classified: "Классифицирована",
    in_progress: "На переработке",
    processed: "Переработана",
    disposed: "Вывезена",
    rejected: "Отклонена",
  };
  return map[status] ?? status;
}
