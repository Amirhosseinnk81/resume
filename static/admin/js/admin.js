document.addEventListener("DOMContentLoaded", function () {

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

});
