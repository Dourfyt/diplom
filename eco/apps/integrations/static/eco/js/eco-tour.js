/**
 * Spotlight onboarding (driver.js) — отдельный тур для каждой вкладки.
 */
(function () {
  function createDriver() {
    var d = window.driver;
    if (!d) return null;
    if (typeof d === "function") return d;
    if (d.js && typeof d.js.driver === "function") return d.js.driver;
    return null;
  }

  function step(selector, title, description, side) {
    var el = document.querySelector(selector);
    if (!el) return null;
    return {
      element: el,
      popover: {
        title: title,
        description: description,
        side: side || "bottom",
        align: "start",
      },
    };
  }

  function commonNavSteps() {
    return [
      step('[data-tour="eco-modules"]', "Модули комплекса", "Переход к API платформы и модулю планирования.", "bottom"),
      step('[data-tour="eco-nav-tabs"]', "Вкладки раздела", "Меню зависит от роли: руководитель видит KPI, эколог — операции и измерения.", "bottom"),
    ].filter(Boolean);
  }

  var PAGE_STEPS = {
    dashboard: function () {
      return commonNavSteps().concat(
        [
          step('[data-tour="eco-page-title"]', "Панель KPI", "Сводные цифры по данным общей базы на сервере.", "bottom"),
          step('[data-tour="eco-kpi-orgs"]', "Организации", "Сколько организаций заведено в справочнике.", "bottom"),
          step('[data-tour="eco-kpi-waste"]', "Виды отходов", "Сколько позиций в справочнике отходов.", "bottom"),
          step('[data-tour="eco-kpi-volume"]', "Общий объём", "Суммарный объём операций в тоннах.", "bottom"),
          step('[data-tour="eco-kpi-recycled"]', "Переработано", "Объём, прошедший переработку.", "bottom"),
          step('[data-tour="eco-kpi-charts"]', "Графики", "Наглядное распределение по видам и периодам.", "top"),
          step("#trainingToggle", "Обучение", "Повторный запуск тура для текущей страницы.", "left"),
        ].filter(Boolean)
      );
    },
    reporting: function () {
      return commonNavSteps().concat(
        [
          step('[data-tour="eco-page-title"]', "Отчётность", "Формирование и просмотр отчётов.", "bottom"),
          step('[data-tour="eco-report-actions"]', "Действия", "Экспорт и фильтры отчётов.", "bottom"),
          step('[data-tour="eco-main"]', "Содержимое", "Таблицы и формы отчёта.", "top"),
        ].filter(Boolean)
      );
    },
    operations: function () {
      return commonNavSteps().concat(
        [
          step('[data-tour="eco-page-title"]', "Журнал операций", "Все движения отходов: приём, переработка, вывоз.", "bottom"),
          step('[data-tour="eco-page-actions"]', "Действия", "Добавление записи и экспорт в Excel/PDF/XML.", "bottom"),
          step('[data-tour="eco-page-table"]', "Таблица", "Каждая строка — операция с датой, типом и объёмом.", "top"),
        ].filter(Boolean)
      );
    },
    monitoring: function () {
      return commonNavSteps().concat(
        [
          step('[data-tour="eco-page-title"]', "Измерения", "Результаты экологического мониторинга.", "bottom"),
          step('[data-tour="eco-page-actions"]', "Добавить измерение", "Новая запись уходит на API платформы.", "bottom"),
          step('[data-tour="eco-page-table"]', "Список измерений", "Показатели, нормативы и дата замера.", "top"),
        ].filter(Boolean)
      );
    },
    waste: function () {
      return commonNavSteps().concat(
        [
          step('[data-tour="eco-page-title"]', "Справочник отходов", "Виды отходов с кодами ФККО и классом опасности.", "bottom"),
          step('[data-tour="eco-page-actions"]', "Управление", "Добавление и редактирование (если доступно).", "bottom"),
          step('[data-tour="eco-page-table"]', "Таблица видов", "Основной список для привязки к операциям.", "top"),
        ].filter(Boolean)
      );
    },
    batches: function () {
      return commonNavSteps().concat(
        [
          step('[data-tour="eco-page-title"]', "Партии", "Данные из модуля учёта — только просмотр.", "bottom"),
          step('[data-tour="eco-page-table"]', "Список партий", "Код, объём, статус и классификация.", "top"),
        ].filter(Boolean)
      );
    },
    organizations: function () {
      return commonNavSteps().concat(
        [
          step('[data-tour="eco-page-title"]', "Организации", "Контрагенты и подразделения площадки.", "bottom"),
          step('[data-tour="eco-page-table"]', "Справочник", "ИНН, адрес и контакты из общей базы.", "top"),
        ].filter(Boolean)
      );
    },
    users: function () {
      return commonNavSteps().concat(
        [
          step('[data-tour="eco-page-title"]', "Пользователи", "Регистрация учётных записей на сервере API.", "bottom"),
          step('[data-tour="eco-page-form"]', "Форма", "Email, пароль, ФИО и роль в системе.", "top"),
        ].filter(Boolean)
      );
    },
    modules: function () {
      return commonNavSteps().concat(
        [
          step('[data-tour="eco-page-title"]', "Модули API", "Список подсистем платформы и их префиксов.", "bottom"),
          step('[data-tour="eco-page-table"]', "Таблица", "Описание каждого модуля комплекса.", "top"),
        ].filter(Boolean)
      );
    },
  };

  var activeDriver = null;

  function setToggleActive(active) {
    var btn = document.getElementById("trainingToggle");
    if (!btn) return;
    btn.textContent = active ? "Тур…" : "Обучение";
    btn.classList.toggle("btn-light", active);
    btn.classList.toggle("btn-warning", !active);
  }

  function stopEcoTour() {
    if (activeDriver) {
      activeDriver.destroy();
      activeDriver = null;
    }
    setToggleActive(false);
  }

  function getPageKey() {
    return document.body.getAttribute("data-nav-active") || "";
  }

  function startEcoTour() {
    var driverFactory = createDriver();
    if (!driverFactory) {
      console.error("driver.js не найден. Проверьте загрузку скрипта.");
      alert("Не удалось запустить обучение: библиотека подсказок не загружена.");
      return;
    }

    var pageKey = getPageKey();
    var build = PAGE_STEPS[pageKey];
    if (!build) {
      build = function () {
        return commonNavSteps().concat(
          [step('[data-tour="eco-main"]', "Страница", "Тур для этого раздела пока общий.", "top")].filter(Boolean)
        );
      };
    }

    var steps = build();
    if (!steps.length) {
      alert("На этой странице нечего показывать в туре.");
      return;
    }

    stopEcoTour();

    activeDriver = driverFactory({
      showProgress: true,
      progressText: "{{current}} из {{total}}",
      nextBtnText: "Далее",
      prevBtnText: "Назад",
      doneBtnText: "Готово",
      allowClose: true,
      overlayOpacity: 0.55,
      stagePadding: 8,
      stageRadius: 12,
      popoverClass: "eco-driver-popover",
      steps: steps,
      onDestroyed: function () {
        activeDriver = null;
        setToggleActive(false);
      },
    });

    setToggleActive(true);
    activeDriver.drive();
  }

  window.startEcoTour = startEcoTour;
  window.stopEcoTour = stopEcoTour;

  function bindButton() {
    var btn = document.getElementById("trainingToggle");
    if (!btn || btn.dataset.tourBound === "1") return;
    btn.dataset.tourBound = "1";
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      if (activeDriver && activeDriver.isActive && activeDriver.isActive()) {
        stopEcoTour();
      } else {
        startEcoTour();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindButton);
  } else {
    bindButton();
  }
})();
