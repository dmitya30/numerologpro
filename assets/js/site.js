(() => {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const revealElements = document.querySelectorAll("[data-reveal]");

  if (reducedMotion || !("IntersectionObserver" in window)) {
    revealElements.forEach((element) => element.classList.add("is-visible"));
  } else {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.14 });

    revealElements.forEach((element) => observer.observe(element));
  }

  const siteHeader = document.querySelector(".site-header");
  const navToggle = document.querySelector(".nav-toggle");
  const navigation = document.querySelector(".site-navigation");

  const updateHeader = () => {
    if (siteHeader) {
      siteHeader.classList.toggle("is-scrolled", window.scrollY > 12);
    }
  };

  updateHeader();
  window.addEventListener("scroll", updateHeader, { passive: true });

  if (siteHeader && navToggle && navigation) {
    const setMenuState = (open, restoreFocus = false) => {
      siteHeader.classList.toggle("is-menu-open", open);
      navToggle.setAttribute("aria-expanded", String(open));
      navToggle.setAttribute("aria-label", open ? "Закрыть меню" : "Открыть меню");
      if (restoreFocus) navToggle.focus();
    };

    navToggle.addEventListener("click", () => {
      const open = navToggle.getAttribute("aria-expanded") !== "true";
      setMenuState(open);
      if (open) {
        const firstLink = navigation.querySelector("a");
        if (firstLink) firstLink.focus();
      }
    });

    navigation.addEventListener("click", (event) => {
      if (event.target.closest("a")) setMenuState(false);
    });

    document.addEventListener("click", (event) => {
      if (navToggle.getAttribute("aria-expanded") === "true" && !siteHeader.contains(event.target)) {
        setMenuState(false);
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && navToggle.getAttribute("aria-expanded") === "true") {
        setMenuState(false, true);
      }
    });

    const desktopQuery = window.matchMedia("(min-width: 721px)");
    const closeOnDesktop = (event) => {
      if (event.matches) setMenuState(false);
    };

    if (desktopQuery.addEventListener) {
      desktopQuery.addEventListener("change", closeOnDesktop);
    } else {
      desktopQuery.addListener(closeOnDesktop);
    }
  }

  if (!reducedMotion) {
    const heroImage = document.querySelector(".hero-picture img");
    window.addEventListener("scroll", () => {
      if (!heroImage || window.scrollY > window.innerHeight) return;
      heroImage.style.transform = `scale(1.025) translateY(${window.scrollY * 0.035}px)`;
    }, { passive: true });
  }
})();
