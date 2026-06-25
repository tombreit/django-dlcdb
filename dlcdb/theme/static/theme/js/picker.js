// SPDX-FileCopyrightText: Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// Reusable live-search picker shared across frontend apps (person, device,
// room, … pickers).
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
//
// Optional `data-multiple="1"` turns the picker into a multi-select: instead of
// a single hidden field, each selected option becomes a card that carries its
// own hidden `<input name="<data-field-name>" value="<id>">`. Picking keeps the
// search open and appends (deduped); the per-card Remove button drops just that
// card (and its hidden input). The form thus submits the live set. A `#<id>-count`
// element, if present, is kept in sync with the number of selected cards.

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
    const removeLabel = picker.dataset.removeLabel || "Remove";
    const fillDateTarget = picker.dataset.fillDateTarget || null;
    const multiple = picker.dataset.multiple === "1";
    const fieldName = picker.dataset.fieldName || null;
    const countEl = document.getElementById(id + "-count");

    // Multi-select has no single hidden field (each card carries its own), so
    // only the single-select mode requires `hiddenInput` to exist.
    if (!multiple && !hiddenInput) {
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

    // Multi-select only: reflect the number of selected cards in the count badge.
    function updateCount() {
      if (countEl) {
        countEl.textContent = selectedSlot.querySelectorAll("[data-option-id]").length;
      }
    }

    // Turn a clicked result option into a proper "selected" card: solid border,
    // a removal button instead of the chevron, no pointer affordances, and any
    // detail affordance (e.g. an "open in admin" link) revealed. The button
    // says "Remove" in multi mode (it drops just this card) and "Change" in
    // single mode (it reopens the search).
    function buildSelectedCard(option) {
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
        changeBtn.innerHTML = '<i class="bi bi-x-lg"></i> ' + (multiple ? removeLabel : changeLabel);
        chevron.replaceWith(changeBtn);
      }

      selectedCard.querySelectorAll(".js-picker-detail").forEach(function (el) {
        el.classList.remove("d-none");
      });

      return selectedCard;
    }

    function selectOption(option) {
      const optionId = option.dataset.optionId;
      if (!optionId) {
        return;
      }

      if (multiple) {
        // Ignore a repeat pick of an already-selected option.
        if (selectedSlot.querySelector('[data-option-id="' + CSS.escape(optionId) + '"]')) {
          closeResults();
          if (searchInput) {
            searchInput.value = "";
          }
          return;
        }

        const selectedCard = buildSelectedCard(option);
        // The card carries its own hidden input, so removing the card removes
        // its value from the submitted set.
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = fieldName;
        input.value = optionId;
        selectedCard.appendChild(input);
        // Prepend so the most recently picked device appears on top of the list.
        selectedSlot.prepend(selectedCard);
        updateCount();

        // Keep the search open so further options can be added.
        closeResults();
        if (searchInput) {
          searchInput.value = "";
          searchInput.focus();
        }

        picker.dispatchEvent(new CustomEvent("picker:selected", { detail: { option: option } }));
        notifyChanged();
        return;
      }

      hiddenInput.value = optionId;
      selectedSlot.replaceChildren(buildSelectedCard(option));

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
        if (multiple) {
          // Remove just this card (and its hidden input); the search stays open.
          const card = clearBtn.closest("[data-option-id]");
          if (card) {
            card.remove();
          }
          updateCount();
          notifyChanged();
        } else {
          clearOption();
        }
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

    // Reflect any server-rendered pre-selected cards in the count badge.
    updateCount();
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
