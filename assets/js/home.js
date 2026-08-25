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

  if (!reducedMotion) {
    const heroImage = document.querySelector(".hero-picture img");
    window.addEventListener("scroll", () => {
      if (!heroImage || window.scrollY > window.innerHeight) return;
      heroImage.style.transform = `scale(1.025) translateY(${window.scrollY * 0.035}px)`;
    }, { passive: true });
  }
})();
