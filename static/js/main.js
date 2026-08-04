document.addEventListener("DOMContentLoaded", () => {

  const body = document.body;
  const navbar = document.getElementById("mainNavbar");
  const themeToggle = document.getElementById("themeToggle");
  const scrollTopBtn = document.getElementById("scrollTopBtn");


  /* =====================================================
     THEME
  ===================================================== */

  const savedTheme =
    localStorage.getItem("theme") || "light";

  applyTheme(savedTheme);


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

        localStorage.setItem(
          "theme",
          nextTheme
        );

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

});