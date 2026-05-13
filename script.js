document.documentElement.classList.add("js");

function initReveal() {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  /* Герой не анимируем: иначе весь блок с текстом стартует с opacity:0 и может
   не получить is-visible у IntersectionObserver — текст «пропадает». */
  const revealTargets = document.querySelectorAll(".section, .card, .site-footer");

  if (reduceMotion) {
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

function loadSiteFooter() {
  const mount = document.getElementById("site-footer-mount");
  if (!mount) {
    initReveal();
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
        mount.outerHTML = trimmed;
      }
    })
    .catch((err) => {
      console.error(err);
    })
    .finally(() => {
      initReveal();
    });
}

loadSiteFooter();
