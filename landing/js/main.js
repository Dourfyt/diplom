const reveals = document.querySelectorAll(".reveal");

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
      }
    });
  },
  { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
);

reveals.forEach((el, index) => {
  el.style.transitionDelay = `${Math.min(index * 40, 320)}ms`;
  observer.observe(el);
});

document.querySelectorAll('a[href^="#"]').forEach((link) => {
  link.addEventListener("click", (event) => {
    const id = link.getAttribute("href");
    if (!id || id === "#") return;
    const target = document.querySelector(id);
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

const headerMenu = document.querySelector(".header-menu");
if (headerMenu) {
  const trigger = headerMenu.querySelector(".menu-trigger");
  const panel = headerMenu.querySelector(".menu-panel");

  const closeMenu = () => {
    headerMenu.classList.remove("open");
    trigger?.setAttribute("aria-expanded", "false");
    panel?.setAttribute("hidden", "");
  };

  const openMenu = () => {
    headerMenu.classList.add("open");
    trigger?.setAttribute("aria-expanded", "true");
    panel?.removeAttribute("hidden");
  };

  trigger?.addEventListener("click", (event) => {
    event.stopPropagation();
    if (headerMenu.classList.contains("open")) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  document.addEventListener("click", (event) => {
    if (!headerMenu.contains(event.target)) {
      closeMenu();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenu();
    }
  });
}
