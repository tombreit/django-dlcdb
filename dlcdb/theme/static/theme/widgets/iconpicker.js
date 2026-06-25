// SPDX-FileCopyrightText: Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// Searchable Bootstrap Icons picker for the DeviceType admin. The icon data is
// embedded as JSON by the widget; this only renders/filters it and writes the
// chosen `bi-<name>` class back into the text input.

(function () {
  "use strict";

  // Cap how many glyphs are rendered at once (the full set is ~2000); searching
  // narrows it down.
  var RENDER_LIMIT = 300;

  function initPicker(root) {
    if (root.dataset.iconpickerReady) {
      return;
    }
    root.dataset.iconpickerReady = "1";

    var dataEl = root.querySelector("[data-iconpicker-data]");
    var icons = [];
    try {
      icons = JSON.parse((dataEl && dataEl.textContent) || "[]");
    } catch (e) {
      icons = [];
    }

    var input = root.querySelector(".bi-iconpicker-field input");
    var previewGlyph = root.querySelector("[data-iconpicker-preview] .bi-iconpicker-glyph");
    var toggle = root.querySelector("[data-iconpicker-toggle]");
    var popup = root.querySelector("[data-iconpicker-popup]");
    var search = root.querySelector("[data-iconpicker-search]");
    var grid = root.querySelector("[data-iconpicker-grid]");
    var empty = root.querySelector("[data-iconpicker-empty]");

    if (!input || !grid) {
      return;
    }

    var charByName = {};
    icons.forEach(function (icon) {
      charByName[icon.name] = icon.char;
    });

    function nameFromValue(value) {
      return (value || "").trim().replace(/^bi-/, "");
    }

    function updatePreview() {
      var name = nameFromValue(input.value);
      var char = charByName[name] || "";
      previewGlyph.textContent = char;
      // Flag a value that is not part of the currently installed set.
      root.classList.toggle("is-unknown", Boolean(input.value.trim()) && !char);
    }

    function render(query) {
      query = (query || "").trim().toLowerCase();
      var frag = document.createDocumentFragment();
      var shown = 0;
      var matches = 0;

      for (var i = 0; i < icons.length; i++) {
        var icon = icons[i];
        if (query && icon.name.indexOf(query) === -1) {
          continue;
        }
        matches++;
        if (shown >= RENDER_LIMIT) {
          continue;
        }

        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "bi-iconpicker-item";
        btn.title = icon.name;
        btn.dataset.name = icon.name;

        var glyph = document.createElement("span");
        glyph.className = "bi-iconpicker-glyph";
        glyph.textContent = icon.char;

        var label = document.createElement("span");
        label.className = "bi-iconpicker-name";
        label.textContent = icon.name;

        btn.appendChild(glyph);
        btn.appendChild(label);
        frag.appendChild(btn);
        shown++;
      }

      grid.replaceChildren(frag);
      empty.hidden = matches !== 0;
    }

    function openPopup() {
      popup.hidden = false;
      render(search.value);
      search.focus();
    }

    function closePopup() {
      popup.hidden = true;
    }

    toggle.addEventListener("click", function () {
      if (popup.hidden) {
        openPopup();
      } else {
        closePopup();
      }
    });

    search.addEventListener("input", function () {
      render(search.value);
    });

    grid.addEventListener("click", function (event) {
      var btn = event.target.closest(".bi-iconpicker-item");
      if (!btn) {
        return;
      }
      input.value = "bi-" + btn.dataset.name;
      updatePreview();
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      closePopup();
    });

    input.addEventListener("input", updatePreview);

    // Click outside closes the popup.
    document.addEventListener("click", function (event) {
      if (!root.contains(event.target)) {
        closePopup();
      }
    });

    updatePreview();
  }

  function init() {
    document.querySelectorAll("[data-iconpicker]").forEach(initPicker);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
