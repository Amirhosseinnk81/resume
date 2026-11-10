document.addEventListener("DOMContentLoaded", () => {

  const body = document.body;
  const navbar = document.getElementById("mainNavbar");
  const themeToggle = document.getElementById("themeToggle");
  const scrollTopBtn = document.getElementById("scrollTopBtn");


  /* =====================================================
     THEME
  ===================================================== */

  // Mirrors the pre-paint script in base.html: an explicit saved choice wins,
  // otherwise follow the OS. Reads are wrapped because localStorage throws in
  // private mode / when site data is blocked.
  function readStoredTheme() {
    try {
      return localStorage.getItem("theme");
    } catch (e) {
      return null;
    }
  }

  function storeTheme(theme) {
    try {
      localStorage.setItem("theme", theme);
    } catch (e) {
      /* non-fatal: the theme still applies for this page view */
    }
  }

  const prefersDark =
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;

  const savedTheme =
    readStoredTheme() || (prefersDark ? "dark" : "light");

  applyTheme(savedTheme);

  // Follow the OS if the visitor has never picked a theme on this site.
  if (window.matchMedia) {
    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", (event) => {
        if (!readStoredTheme()) {
          applyTheme(event.matches ? "dark" : "light");
        }
      });
  }


  function applyTheme(theme) {

    body.setAttribute(
      "data-theme",
      theme
    );

    if (!themeToggle) {
      return;
    }

    const icon =
      themeToggle.querySelector("i");

    if (!icon) {
      return;
    }

    if (theme === "dark") {

      icon.className =
        "fa-solid fa-sun";

      themeToggle.setAttribute(
        "aria-label",
        "فعال کردن حالت روشن"
      );

      themeToggle.setAttribute(
        "title",
        "حالت روشن"
      );

    } else {

      icon.className =
        "fa-solid fa-moon";

      themeToggle.setAttribute(
        "aria-label",
        "فعال کردن حالت تاریک"
      );

      themeToggle.setAttribute(
        "title",
        "حالت تاریک"
      );

    }

  }


  if (themeToggle) {

    themeToggle.addEventListener(
      "click",
      () => {

        const currentTheme =
          body.getAttribute(
            "data-theme"
          );

        const nextTheme =
          currentTheme === "dark"
            ? "light"
            : "dark";

        applyTheme(nextTheme);

        storeTheme(nextTheme);

      }
    );

  }


  /* =====================================================
     NAVBAR SCROLL
  ===================================================== */

  function handleScroll() {

    const scrollY =
      window.scrollY;

    if (navbar) {

      if (scrollY > 40) {

        navbar.classList.add(
          "scrolled"
        );

      } else {

        navbar.classList.remove(
          "scrolled"
        );

      }

    }


    /* Scroll To Top */

    if (scrollTopBtn) {

      if (scrollY > 350) {

        scrollTopBtn.style.display =
          "flex";

      } else {

        scrollTopBtn.style.display =
          "none";

      }

    }

  }


  window.addEventListener(
    "scroll",
    handleScroll,
    { passive: true }
  );


  handleScroll();


  /* =====================================================
     SCROLL TO TOP
  ===================================================== */

  if (scrollTopBtn) {

    scrollTopBtn.addEventListener(
      "click",
      () => {

        window.scrollTo({
          top: 0,
          behavior: "smooth"
        });

      }
    );

  }


  /* =====================================================
     FADE ITEMS
  ===================================================== */

  const fadeItems =
    document.querySelectorAll(
      ".fade-item"
    );


  if (
    fadeItems.length &&
    "IntersectionObserver" in window
  ) {

    const observer =
      new IntersectionObserver(
        (entries, observerInstance) => {

          entries.forEach(
            (entry) => {

              if (
                entry.isIntersecting
              ) {

                entry.target.classList.add(
                  "visible"
                );

                observerInstance.unobserve(
                  entry.target
                );

              }

            }
          );

        },
        {
          threshold: 0.15
        }
      );


    fadeItems.forEach(
      (item) => {

        observer.observe(item);

      }
    );

  }


  /* =====================================================
     ACTIVE NAV LINK
  ===================================================== */

  const currentPath =
    window.location.pathname;

  const navLinks =
    document.querySelectorAll(
      "#mainNavbar .nav-link"
    );


  navLinks.forEach(
    (link) => {

      const href =
        link.getAttribute("href");

      if (!href) {
        return;
      }


      if (
        href !== "/" &&
        currentPath.startsWith(href)
      ) {

        link.classList.add(
          "active"
        );

      }


      if (
        href === "/" &&
        currentPath === "/"
      ) {

        link.classList.add(
          "active"
        );

      }

    }
  );


  /* =====================================================
     SCROLL REVEAL  (replaces the AOS library)

     AOS shipped 2.2 KB of CSS + 4.5 KB of JS from a separate CDN origin to
     do one thing: add a class when an element scrolls into view. This does
     the same with IntersectionObserver and reads the existing data-aos /
     data-aos-delay attributes, so no template markup had to change.
  ===================================================== */

  const revealTargets =
    document.querySelectorAll("[data-aos]");

  if (revealTargets.length) {

    // Honour the OS "reduce motion" setting: show everything immediately
    // rather than animating. AOS did not do this.
    const reduceMotion =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reduceMotion || !("IntersectionObserver" in window)) {

      revealTargets.forEach((el) => el.classList.add("reveal-visible"));

    } else {

      revealTargets.forEach((el) => {

        el.classList.add("reveal");

        const delay = el.getAttribute("data-aos-delay");

        if (delay) {
          el.style.setProperty("--reveal-delay", `${parseInt(delay, 10)}ms`);
        }

      });

      const observer = new IntersectionObserver(
        (entries) => {

          entries.forEach((entry) => {

            if (entry.isIntersecting) {
              entry.target.classList.add("reveal-visible");
              observer.unobserve(entry.target);
            }

          });

        },
        { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
      );

      revealTargets.forEach((el) => observer.observe(el));

    }

  }

});
