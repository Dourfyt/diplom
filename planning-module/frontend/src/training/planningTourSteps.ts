import type { DriveStep } from "driver.js";
import type { PlanningTab } from "./planningTour";

type Pop = NonNullable<DriveStep["popover"]>;

function step(element: string, title: string, description: string, popover?: Partial<Pop>): DriveStep {
  return {
    element,
    popover: {
      title,
      description,
      side: "bottom",
      align: "start",
      ...popover,
    },
  };
}

/** Тур только для текущей вкладки — по каждому блоку интерфейса. */
export function getStepsForTab(tab: PlanningTab): DriveStep[] {
  const common: DriveStep[] = [
    step(
      '[data-tour="topbar-title"]',
      "Заголовок раздела",
      "Здесь название и краткое описание того, что вы видите на этой вкладке.",
      { side: "bottom" }
    ),
    step(
      '[data-tour="context-bar"]',
      "Контекст плана",
      "Показывает выбранный план, утверждённую версию и горизонт планирования. Всегда сверяйтесь с этой строкой перед решениями.",
      { side: "bottom" }
    ),
  ];

  const byTab: Record<PlanningTab, DriveStep[]> = {
    dashboard: [
      step(
        '[data-tour="kpi-oee"]',
        "OEE оборудования",
        "Overall Equipment Effectiveness — насколько эффективно работают линии L1 и L2. Чем выше %, тем меньше простоев.",
        { side: "bottom" }
      ),
      step(
        '[data-tour="kpi-completion"]',
        "Выполнение плана",
        "Сколько партий из очереди уже попало в расписание. 100% — все учтённые партии распределены по линиям.",
        { side: "bottom" }
      ),
      step(
        '[data-tour="kpi-idle"]',
        "Суммарный простой",
        "Часы, когда линии простаивают в рамках текущего плана. Рост простоя — сигнал пересмотреть расписание.",
        { side: "bottom" }
      ),
      step(
        '[data-tour="kpi-storage"]',
        "Риск хранения",
        "Число партий, у которых до конца допустимого срока хранения осталось меньше 6 часов. Требует срочного планирования.",
        { side: "bottom" }
      ),
      step(
        '[data-tour="kpi-priority"]',
        "Средний приоритет",
        "Средний балл приоритета партий в очереди. Планировщик сначала ставит в расписание партии с более высоким приоритетом.",
        { side: "bottom" }
      ),
      step(
        '[data-tour="kpi-notifications"]',
        "Уведомления",
        "Сколько оповещений ещё не подтверждено. Перейдите во вкладку «Уведомления», чтобы обработать их.",
        { side: "bottom" }
      ),
      step(
        '[data-tour="quick-actions"]',
        "Быстрые действия",
        "Кнопки перехода к расписанию, партиям и симуляции без поиска в меню слева.",
        { side: "top" }
      ),
      step(
        '[data-tour="lines-utilization"]',
        "Загрузка линий",
        "Доля загрузки L1 и L2 в текущем плане. Помогает увидеть «узкое место» производства.",
        { side: "top" }
      ),
      step(
        '[data-tour="btn-new-plan"]',
        "Новый план",
        "Строит сменное расписание по партиям из очереди. После создания откройте вкладку «Расписание».",
        { side: "left", align: "end" }
      ),
      step(
        '[data-tour="plan-picker"]',
        "Выбор плана",
        "Список версий планов. Можно включить историю и сравнить черновики с утверждённым планом.",
        { side: "left", align: "end" }
      ),
    ],
    schedule: [
      step(
        '[data-tour="schedule-toolbar"]',
        "Панель действий",
        "Здесь утверждение плана и перепланирование при аварийной остановке линии.",
        { side: "bottom" }
      ),
      step(
        '[data-tour="schedule-approve"]',
        "Утвердить план",
        "Фиксирует расписание и синхронизирует этапы с модулем мониторинга. Доступно только для черновика.",
        { side: "bottom" }
      ),
      step(
        '[data-tour="schedule-replan"]',
        "Перепланировать",
        "Пересчёт расписания при простое линии L2 (8 ч). Используйте при сбоях оборудования.",
        { side: "bottom" }
      ),
      step(
        '[data-tour="schedule-plan-header"]',
        "Шапка плана",
        "Название, версия, горизонт в часах и статус: черновик, утверждён или симуляция.",
        { side: "bottom" }
      ),
      step(
        '[data-tour="schedule-gantt"]',
        "Диаграмма Gantt",
        "Полосы — операции на линиях во времени. Длина полосы = длительность переработки партии.",
        { side: "top" }
      ),
      step(
        '[data-tour="schedule-table"]',
        "Таблица операций",
        "Детали: код партии, линия, начало/конец, выход и потери в тоннах, приоритет.",
        { side: "top" }
      ),
      step('[data-tour="plan-picker"]', "Выбор плана", "Переключите другой план, если смотрите не тот вариант.", {
        side: "left",
        align: "end",
      }),
    ],
    batches: [
      step(
        '[data-tour="batches-header"]',
        "Очередь партий",
        "Список партий, ожидающих переработки. Сортировка по приоритету планировщика.",
        { side: "bottom" }
      ),
      step(
        '[data-tour="batches-search"]',
        "Поиск",
        "Фильтр по коду или наименованию. Удобно, когда партий много.",
        { side: "bottom" }
      ),
      step(
        '[data-tour="batches-col-code"]',
        "Код партии",
        "Уникальный идентификатор из модуля учёта (например WB-…).",
        { side: "right" }
      ),
      step(
        '[data-tour="batches-col-balance"]',
        "Баланс тонн",
        "Поступило — сколько приняли; переработано и вывезено — по журналу; остаток — что ещё на площадке.",
        { side: "left" }
      ),
      step(
        '[data-tour="batches-col-storage"]',
        "Хранение",
        "Сколько часов осталось до риска по сроку хранения. Метка «риск» — меньше 6 часов.",
        { side: "left" }
      ),
      step(
        '[data-tour="batches-col-priority"]',
        "Приоритет",
        "Чем выше полоска и число, тем раньше партия попадёт в план.",
        { side: "left" }
      ),
      step(
        '[data-tour="batches-col-route"]',
        "Маршрут",
        "Последовательность линий переработки (L1, L2…).",
        { side: "left" }
      ),
    ],
    simulation: [
      step(
        '[data-tour="simulation-scenarios"]',
        "Сценарии",
        "Три варианта «что если»: без изменений, ускоренный горизонт, аварийная остановка L2.",
        { side: "bottom" }
      ),
      step(
        '[data-tour="simulation-baseline"]',
        "Базовый сценарий",
        "Копия текущего плана без изменений — эталон для сравнения.",
        { side: "right" }
      ),
      step(
        '[data-tour="simulation-accelerated"]',
        "Ускоренный",
        "Горизонт плана сокращён на 15% — оценка, успеете ли быстрее.",
        { side: "bottom" }
      ),
      step(
        '[data-tour="simulation-emergency"]',
        "Аварийный",
        "Имитация остановки L2 на 8 часов — смотрите, как сдвигаются операции.",
        { side: "left" }
      ),
      step(
        '[data-tour="simulation-result"]',
        "Результат сравнения",
        "Таблица отличий: простой, риск хранения, OEE. Зелёное изменение — улучшение.",
        { side: "top" }
      ),
    ],
    notifications: [
      step(
        '[data-tour="notifications-header"]',
        "Центр уведомлений",
        "Сообщения о простоях (T1) и сроках хранения (T2).",
        { side: "bottom" }
      ),
      step(
        '[data-tour="notifications-list"]',
        "Список оповещений",
        "Каждая карточка — проблема по текущему плану. Нажмите «Подтвердить», когда приняли меры.",
        { side: "top" }
      ),
    ],
  };

  const navStep = step(
    `[data-tour="nav-${tab}"]`,
    `Вкладка «${tabLabel(tab)}»`,
    "Вы находитесь в этом разделе. Остальные вкладки — в меню слева.",
    { side: "right", align: "start" }
  );

  return [navStep, ...common, ...byTab[tab]];
}

function tabLabel(tab: PlanningTab): string {
  const labels: Record<PlanningTab, string> = {
    dashboard: "Обзор",
    schedule: "Расписание",
    batches: "Партии",
    simulation: "Симуляция",
    notifications: "Уведомления",
  };
  return labels[tab];
}
