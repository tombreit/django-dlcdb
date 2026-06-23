// SPDX-FileCopyrightText: 2026 Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// Person picker for the lending detail view.
//
// The live search (#person-results) is rendered by HTMX. Selecting a result
// copies it into the persistent #person-selected slot and writes the chosen id
// into the hidden form field (#id_person). Keeping the hidden field outside the
// HTMX swap region means the selection survives keystrokes and validation
// re-renders.

(function () {
  "use strict";

  function init() {
    const picker = document.getElementById("person-picker");
    if (!picker) {
      return;
    }

    const hiddenInput = document.getElementById("id_person");
    const selectedSlot = document.getElementById("person-selected");
    const searchWrap = document.getElementById("person-search-wrap");
    const searchInput = document.getElementById("person-search-input");
    const resultsBox = document.getElementById("person-results");
    const locked = picker.dataset.personLocked === "1";
    const changeLabel = picker.dataset.changeLabel || "Change";

    function selectPerson(option) {
      const personId = option.dataset.personId;
      if (!personId) {
        return;
      }
      hiddenInput.value = personId;

      // Reuse the clicked option markup as the selected card, then turn it into
      // a proper "selected" card (solid border, a Change button instead of the
      // chevron, no pointer affordances).
      const selectedCard = option.cloneNode(true);
      selectedCard.classList.remove("person-option", "border-0", "mb-1");
      selectedCard.classList.add("mb-2");
      selectedCard.style.cursor = "";
      selectedCard.removeAttribute("role");

      const chevron = selectedCard.querySelector(".bi-chevron-right");
      if (chevron) {
        const changeBtn = document.createElement("button");
        changeBtn.type = "button";
        changeBtn.className = "js-person-clear btn btn-sm btn-outline-secondary";
        changeBtn.innerHTML = '<i class="bi bi-x-lg"></i> ' + changeLabel;
        chevron.replaceWith(changeBtn);
      }

      selectedSlot.replaceChildren(selectedCard);

      // Collapse the search UI.
      searchWrap.classList.add("d-none");
      closeResults();
      if (searchInput) {
        searchInput.value = "";
      }
    }

    function clearPerson() {
      hiddenInput.value = "";
      selectedSlot.replaceChildren();
      searchWrap.classList.remove("d-none");
      closeResults();
      if (searchInput) {
        searchInput.focus();
      }
    }

    function closeResults() {
      if (resultsBox) {
        resultsBox.replaceChildren();
      }
    }

    // Event delegation: results are swapped in by HTMX, the selected card by us.
    document.addEventListener("click", function (event) {
      if (locked) {
        return;
      }

      const clearBtn = event.target.closest(".js-person-clear");
      if (clearBtn && picker.contains(clearBtn)) {
        event.preventDefault();
        clearPerson();
        return;
      }

      const option = event.target.closest(".js-person-option");
      if (option && resultsBox && resultsBox.contains(option)) {
        event.preventDefault();
        selectPerson(option);
        return;
      }

      // Click outside the picker closes the results dropdown.
      if (!picker.contains(event.target)) {
        closeResults();
      }
    });

    // Keep Enter in the search box from submitting the whole lending form.
    if (searchInput) {
      searchInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault();
        }
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
