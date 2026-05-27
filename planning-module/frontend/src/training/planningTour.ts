import { driver, type Driver } from "driver.js";
import "driver.js/dist/driver.css";
import "./driver-theme.css";
import { getStepsForTab } from "./planningTourSteps";

export type PlanningTab =
  | "dashboard"
  | "schedule"
  | "batches"
  | "simulation"
  | "notifications";

type StartOptions = {
  tab: PlanningTab;
  setTab: (tab: PlanningTab) => void;
  onStart?: () => void;
  onEnd?: () => void;
};

let activeDriver: Driver | null = null;

function filterSteps(steps: ReturnType<typeof getStepsForTab>) {
  return steps.filter(
    (s) => !s.element || document.querySelector(String(s.element))
  );
}

export function stopPlanningTour() {
  activeDriver?.destroy();
  activeDriver = null;
}

export function isPlanningTourActive() {
  return Boolean(activeDriver?.isActive?.());
}

export function startPlanningTour({ tab, setTab, onStart, onEnd }: StartOptions) {
  stopPlanningTour();
  setTab(tab);

  const run = () => {
    const steps = filterSteps(getStepsForTab(tab));
    if (!steps.length) return;

    const driverObj = driver({
      showProgress: true,
      progressText: "{{current}} из {{total}}",
      nextBtnText: "Далее",
      prevBtnText: "Назад",
      doneBtnText: "Готово",
      allowClose: true,
      overlayOpacity: 0.55,
      stagePadding: 8,
      stageRadius: 12,
      popoverClass: "planning-driver-popover",
      steps,
      onDestroyed: () => {
        activeDriver = null;
        onEnd?.();
      },
    });

    activeDriver = driverObj;
    onStart?.();
    driverObj.drive();
  };

  window.setTimeout(run, 220);
}
