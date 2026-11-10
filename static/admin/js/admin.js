document.addEventListener("DOMContentLoaded", function () {

    initThemeToggle();
    initTooltips();
    initSkillRows();

});

// The attribute itself is set before first paint by the inline script in
// admin/base.html; this only wires up the button. The "theme" key is the
// one the public site uses, so the choice carries across both.
function initThemeToggle() {

    var toggle = document.getElementById("themeToggle");

    if (!toggle) {
        return;
    }

    var root = document.documentElement;
    var icon = toggle.querySelector("i");

    function render() {
        var dark = root.getAttribute("data-bs-theme") === "dark";

        if (icon) {
            icon.className = dark ? "bi bi-sun" : "bi bi-moon";
        }

        toggle.setAttribute("aria-label", dark ? "تم روشن" : "تم تیره");
        toggle.setAttribute("aria-pressed", dark ? "true" : "false");
    }

    toggle.addEventListener("click", function () {
        var next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";

        root.setAttribute("data-bs-theme", next);

        try {
            localStorage.setItem("theme", next);
        } catch (error) {
            /* non-fatal: the theme still applies for this page view */
        }

        render();
    });

    render();

}

function initTooltips() {

    if (!window.bootstrap || !window.bootstrap.Tooltip) {
        return;
    }

    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (element) {
        new window.bootstrap.Tooltip(element);
    });

}

function initSkillRows() {

    var addBtn = document.getElementById("addSkillRow");
    var rowsContainer = document.getElementById("skillRows");
    var template = document.getElementById("skillRowTemplate");

    if (!addBtn || !rowsContainer || !template) {
        return;
    }

    addBtn.addEventListener("click", function () {
        var clone = template.content.cloneNode(true);
        rowsContainer.appendChild(clone);
    });

    rowsContainer.addEventListener("click", function (event) {
        var removeBtn = event.target.closest(".remove-skill-row");

        if (!removeBtn) {
            return;
        }

        var row = removeBtn.closest(".skill-row");

        if (row) {
            row.remove();
        }
    });

}
