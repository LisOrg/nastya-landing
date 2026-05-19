document.documentElement.classList.add("js");

function initReveal() {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  /* Hero-секции намеренно исключены: они в viewport при загрузке и могут не пройти
     IntersectionObserver вовремя, оставив текст с opacity:0.
     .card намеренно исключены: они вложены в .section, двойной transform сдвигал
     кнопки на 40px и делал их недоступными при нажатии. */
  const revealTargets = document.querySelectorAll(
    ".section:not(.main-hero):not(.psy-hero):not(.chem-hero), .site-footer"
  );

  if (reduceMotion || !("IntersectionObserver" in window)) {
    revealTargets.forEach((item) => item.classList.add("is-visible"));
    return;
  }

  revealTargets.forEach((item, index) => {
    item.classList.add("reveal-item");
    item.style.setProperty("--reveal-delay", `${Math.min(index % 6, 5) * 70}ms`);
  });

  const observer = new IntersectionObserver(
    (entries, obs) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) {
          return;
        }

        entry.target.classList.add("is-visible");
        obs.unobserve(entry.target);
      });
    },
    {
      threshold: 0.12,
      rootMargin: "0px 0px -8% 0px",
    },
  );

  revealTargets.forEach((item) => observer.observe(item));
}

function initProcessSlider() {
  const block = document.querySelector("[data-process-slider]");
  if (!block) {
    return;
  }

  const slider = block.querySelector(".process-slider");
  const prev = block.querySelector("[data-slider-prev]");
  const next = block.querySelector("[data-slider-next]");
  const slides = slider ? slider.querySelectorAll(".process-slide") : [];

  if (!slider || slides.length === 0) {
    return;
  }

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function slideStep() {
    const first = slides[0];
    const styles = getComputedStyle(slider);
    const gapRaw = styles.columnGap || styles.gap || "0";
    const gap = Number.parseFloat(gapRaw) || 0;
    return first.offsetWidth + gap;
  }

  function updateNav() {
    const maxScroll = Math.max(0, slider.scrollWidth - slider.clientWidth - 2);
    if (prev) {
      prev.disabled = slider.scrollLeft <= 2;
    }
    if (next) {
      next.disabled = slider.scrollLeft >= maxScroll;
    }
  }

  function scrollByDir(dir) {
    slider.scrollBy({
      left: dir * slideStep(),
      behavior: reduceMotion ? "auto" : "smooth",
    });
  }

  prev?.addEventListener("click", () => scrollByDir(-1));
  next?.addEventListener("click", () => scrollByDir(1));

  slider.classList.add("process-slider--mouse-drag");

  let dragPointerId = null;
  let dragStartX = 0;
  let dragStartScroll = 0;

  function onPointerDown(e) {
    if (e.pointerType !== "mouse" || e.button !== 0) {
      return;
    }
    dragPointerId = e.pointerId;
    dragStartX = e.clientX;
    dragStartScroll = slider.scrollLeft;
    slider.setPointerCapture(e.pointerId);
    slider.classList.add("is-dragging");
  }

  function onPointerMove(e) {
    if (dragPointerId !== e.pointerId) {
      return;
    }
    slider.scrollLeft = dragStartScroll - (e.clientX - dragStartX);
    e.preventDefault();
  }

  function onPointerUp(e) {
    if (dragPointerId !== e.pointerId) {
      return;
    }
    dragPointerId = null;
    try {
      slider.releasePointerCapture(e.pointerId);
    } catch {
      /* уже отпущен */
    }
    slider.classList.remove("is-dragging");
  }

  slider.addEventListener("pointerdown", onPointerDown);
  slider.addEventListener("pointermove", onPointerMove, { passive: false });
  slider.addEventListener("pointerup", onPointerUp);
  slider.addEventListener("pointercancel", onPointerUp);

  slider.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      scrollByDir(-1);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      scrollByDir(1);
    }
  });

  slider.addEventListener("scroll", updateNav, { passive: true });
  window.addEventListener("resize", updateNav);
  updateNav();
}

function initHamburgerMenu() {
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.getElementById("header-nav");

  if (!toggle || !nav) return;

  function closeMenu() {
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "Открыть меню");
    nav.classList.remove("is-open");
  }

  function openMenu() {
    toggle.setAttribute("aria-expanded", "true");
    toggle.setAttribute("aria-label", "Закрыть меню");
    nav.classList.add("is-open");
  }

  toggle.addEventListener("click", () => {
    toggle.getAttribute("aria-expanded") === "true" ? closeMenu() : openMenu();
  });

  // Закрыть по клику на якорную ссылку (#...).
  // Для ссылок на другие страницы (.html) меню НЕ закрываем немедленно:
  // ряд мобильных браузеров перестаёт следовать href, если родитель
  // становится display:none в процессе обработки того же click-события.
  // При навигации на новую страницу меню исчезнет автоматически.
  nav.addEventListener("click", (e) => {
    const link = e.target.closest("a");
    if (!link) return;
    const href = link.getAttribute("href") || "";
    if (href.startsWith("#")) closeMenu();
  });

  // Закрыть по клику вне меню
  document.addEventListener("click", (e) => {
    if (!toggle.contains(e.target) && !nav.contains(e.target)) closeMenu();
  });

  // Закрыть по Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
      closeMenu();
      toggle.focus();
    }
  });

  // Закрыть при расширении окна выше мобильного breakpoint
  window.matchMedia("(min-width: 641px)").addEventListener("change", (e) => {
    if (e.matches) closeMenu();
  });
}

function loadSiteFooter() {
  const mount = document.getElementById("site-footer-mount");
  if (!mount) {
    initReveal();
    initProcessSlider();
    return;
  }

  // Футер уже вставлен статически — fetch не нужен
  if (mount.querySelector("footer")) {
    initReveal();
    initProcessSlider();
    return;
  }

  const footerUrl = new URL("footer.html", window.location.href);

  fetch(footerUrl.href)
    .then((res) => {
      if (!res.ok) {
        throw new Error(`Footer: HTTP ${res.status}`);
      }
      return res.text();
    })
    .then((html) => {
      const trimmed = html.trim();
      if (trimmed) {
        mount.innerHTML = trimmed;
      }
    })
    .catch((err) => {
      console.error(err);
    })
    .finally(() => {
      initReveal();
      initProcessSlider();
    });
}

initHamburgerMenu();
loadSiteFooter();
