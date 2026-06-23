// SPDX-FileCopyrightText: 2026 Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// Reusable live-search picker for the lending app (person and device pickers).
//
// Each `[data-picker]` element drives its own hidden form field. The live
// search results (`#<id>-results`) are rendered by HTMX; selecting a result
// copies it into the persistent `#<id>-selected` slot and writes the chosen id
// into the hidden field named by `data-field-id`. Keeping the hidden field
// outside the HTMX swap region means the selection survives keystrokes and
// validation re-renders.
//
// Optional `data-fill-date-target` lets a picker prefill a date input (e.g. the
// desired-return-date from a person's contract end via `data-contract-end` on
// the option), only when that input is still empty and the date is not in the
// past.

(function () {
  "use strict";

  function initPicker(picker) {
    const id = picker.dataset.pickerId;
    const hiddenInput = document.getElementById(picker.dataset.fieldId);
    const selectedSlot = document.getElementById(id + "-selected");
    const searchWrap = document.getElementById(id + "-search-wrap");
    const searchInput = document.getElementById(id + "-search-input");
    const resultsBox = document.getElementById(id + "-results");
    const locked = picker.dataset.locked === "1";
    const changeLabel = picker.dataset.changeLabel || "Change";
    const fillDateTarget = picker.dataset.fillDateTarget || null;

    if (!hiddenInput) {
      return;
    }

    function maybeFillDate(option) {
      if (!fillDateTarget) {
        return;
      }
      const target = document.getElementById(fillDateTarget);
      if (!target || target.value) {
        return; // only fill when empty, never override a manual entry
      }
      const contractEnd = option.dataset.contractEnd;
      if (!contractEnd) {
        return; // no contract end on this option
      }
      const today = new Date().toISOString().slice(0, 10);
      if (contractEnd < today) {
        return; // a past contract end is not a sensible default
      }
      target.value = contractEnd;
    }

    function notifyChanged() {
      document.dispatchEvent(new CustomEvent("picker:changed", { detail: { pickerId: id } }));
    }

    function selectOption(option) {
      const optionId = option.dataset.optionId;
      if (!optionId) {
        return;
      }
      hiddenInput.value = optionId;

      // Reuse the clicked option markup as the selected card, then turn it into
      // a proper "selected" card (solid border, a Change button instead of the
      // chevron, no pointer affordances).
      const selectedCard = option.cloneNode(true);
      selectedCard.classList.remove("js-picker-option", "picker-option", "picker-active", "border-0", "mb-1");
      selectedCard.classList.add("mb-2");
      selectedCard.style.cursor = "";
      selectedCard.style.backgroundColor = "";
      selectedCard.removeAttribute("role");

      const chevron = selectedCard.querySelector(".bi-chevron-right");
      if (chevron) {
        const changeBtn = document.createElement("button");
        changeBtn.type = "button";
        changeBtn.className = "js-picker-clear btn btn-sm btn-outline-secondary";
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

      maybeFillDate(option);
      // Let the option side-effect any extra wiring (e.g. room prefill).
      picker.dispatchEvent(new CustomEvent("picker:selected", { detail: { option: option } }));
      notifyChanged();
    }

    function clearOption() {
      hiddenInput.value = "";
      selectedSlot.replaceChildren();
      searchWrap.classList.remove("d-none");
      closeResults();
      if (searchInput) {
        searchInput.focus();
      }
      notifyChanged();
    }

    function closeResults() {
      if (resultsBox) {
        resultsBox.replaceChildren();
      }
    }

    // --- Keyboard navigation over the result options -------------------------

    function getOptions() {
      return resultsBox ? Array.from(resultsBox.querySelectorAll(".js-picker-option")) : [];
    }

    function setActive(options, index) {
      options.forEach(function (option, i) {
        if (i === index) {
          option.classList.add("picker-active");
          option.style.backgroundColor = "var(--bs-tertiary-bg)";
          option.scrollIntoView({ block: "nearest" });
        } else {
          option.classList.remove("picker-active");
          option.style.backgroundColor = "";
        }
      });
    }

    function activeIndex(options) {
      return options.findIndex(function (option) {
        return option.classList.contains("picker-active");
      });
    }

    // Highlight the top match after each live-search swap so Enter / arrows
    // feel natural straight away.
    if (resultsBox) {
      resultsBox.addEventListener("htmx:afterSwap", function () {
        const options = getOptions();
        if (options.length) {
          setActive(options, 0);
        }
      });
    }

    // Event delegation: results are swapped in by HTMX, the selected card by us.
    document.addEventListener("click", function (event) {
      if (locked) {
        return;
      }

      const clearBtn = event.target.closest(".js-picker-clear");
      if (clearBtn && picker.contains(clearBtn)) {
        event.preventDefault();
        clearOption();
        return;
      }

      const option = event.target.closest(".js-picker-option");
      if (option && resultsBox && resultsBox.contains(option)) {
        event.preventDefault();
        selectOption(option);
        return;
      }

      // Click outside this picker closes its results dropdown.
      if (!picker.contains(event.target)) {
        closeResults();
      }
    });

    // Arrow keys move the highlight, Enter selects, Escape closes. Enter is also
    // prevented from submitting the enclosing form.
    if (searchInput) {
      searchInput.addEventListener("keydown", function (event) {
        if (locked) {
          return;
        }
        const options = getOptions();

        if (event.key === "ArrowDown") {
          event.preventDefault();
          if (!options.length) {
            return;
          }
          const i = activeIndex(options);
          setActive(options, i < options.length - 1 ? i + 1 : 0);
        } else if (event.key === "ArrowUp") {
          event.preventDefault();
          if (!options.length) {
            return;
          }
          const i = activeIndex(options);
          setActive(options, i > 0 ? i - 1 : options.length - 1);
        } else if (event.key === "Enter") {
          event.preventDefault();
          const i = activeIndex(options);
          if (i >= 0) {
            selectOption(options[i]);
          } else if (options.length === 1) {
            selectOption(options[0]);
          }
        } else if (event.key === "Escape") {
          closeResults();
        }
      });
    }
  }

  function init() {
    document.querySelectorAll("[data-picker]").forEach(initPicker);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
