// SPDX-FileCopyrightText: Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// Filterbar behavior (see theme/templates/theme/filterbar/).
//
// All listeners are delegated at document level, so nothing needs to be
// (re-)initialized after HTMX swaps. The <form data-filterbar> is the single
// source of truth: chips and sort headers never issue their own requests via
// JS — they update the form's inputs and dispatch one bubbling "change",
// which fires the form's own hx-get.

function ownerForm(el) {
    return document.getElementById(el.dataset.filterbarForm);
}

// Rewrite a dropdown button label from its checked input(s):
// "State" -> "State: Overdue".
function updateDropdownLabel(dropdown) {
    const button = dropdown.querySelector('[data-filterbar-label]');
    const labelSpan = dropdown.querySelector('[data-filterbar-btn-label]');
    if (!button || !labelSpan) return;

    const selectedOptions = [...dropdown.querySelectorAll('input:checked')]
        .filter((input) => input.value !== '')
        .map((input) => input.parentElement.querySelector('[data-filterbar-option]'));

    const base = button.dataset.filterbarLabel;
    if (selectedOptions.length === 0) {
        labelSpan.textContent = base;
    } else if (selectedOptions.length === 1) {
        labelSpan.innerHTML = `${base}: ${selectedOptions[0].innerHTML}`;
    } else {
        labelSpan.textContent = `${base}: ${selectedOptions.length}`;
    }
}

// Update all dropdown labels and the mobile "Filters (n)" badge of a form.
function updateFormLabels(form) {
    form.querySelectorAll('.filterbar-filter').forEach(updateDropdownLabel);

    const badge = form.querySelector('[data-filterbar-count]');
    if (badge) {
        const count = [...form.querySelectorAll('.filterbar-filter:not(.filterbar-sort) input:checked')]
            .filter((input) => input.value !== '').length;
        badge.textContent = count;
        badge.classList.toggle('d-none', count === 0);
    }
}

// Reset one input to its "off" state; for checkboxes, only when it carries
// `value` (undefined = any value). Radios fall back to their empty "reset" choice.
function resetInput(input, value) {
    if (input.type === 'radio') {
        input.checked = input.value === '';
    } else if (input.type === 'checkbox') {
        if (value === undefined || input.value === value) input.checked = false;
    } else {
        input.value = '';
    }
}

// Clear one parameter of the form; for multi-value params (checkboxes) only
// the given value.
function clearParam(form, param, value) {
    form.querySelectorAll(`[name="${CSS.escape(param)}"]`).forEach((input) => resetInput(input, value));
}

document.addEventListener('change', (event) => {
    const form = event.target.closest('form[data-filterbar]');
    if (form) updateFormLabels(form);
});

document.addEventListener('click', (event) => {
    // Chip "x": clear that one value, then submit through the form.
    const chip = event.target.closest('[data-filterbar-remove]');
    if (chip) {
        const form = ownerForm(chip);
        if (!form) return; // no bar on this page -> let the href do a full reload
        event.preventDefault();
        clearParam(form, chip.dataset.filterbarRemove, chip.dataset.filterbarValue);
        form.dispatchEvent(new Event('change', { bubbles: true }));
        return;
    }

    // "Clear all": reset search + every filter, keep the sort order.
    const clearAll = event.target.closest('[data-filterbar-clear-all]');
    if (clearAll) {
        const form = ownerForm(clearAll);
        if (!form) return;
        event.preventDefault();
        form.querySelectorAll('input[type="search"], .filterbar-filter:not(.filterbar-sort) input').forEach(
            (input) => resetInput(input)
        );
        form.dispatchEvent(new Event('change', { bubbles: true }));
        return;
    }

    // Sortable column header: the link's own hx-get fetches the sorted list;
    // here we only sync the bar's sort radio + button label so the form does
    // not resubmit a stale ordering on the next filter change.
    const sortLink = event.target.closest('[data-filterbar-ordering]');
    if (sortLink) {
        document.querySelectorAll('form[data-filterbar]').forEach((form) => {
            const radio = form.querySelector(
                `.filterbar-sort input[value="${CSS.escape(sortLink.dataset.filterbarOrdering)}"]`
            );
            if (radio) {
                radio.checked = true;
                updateFormLabels(form);
            }
        });
    }
});

// In-menu option filter for long choice lists.
document.addEventListener('input', (event) => {
    if (!event.target.matches('[data-filterbar-menufilter]')) return;
    const query = event.target.value.toLowerCase();
    event.target.closest('.dropdown-menu').querySelectorAll('label.dropdown-item').forEach((item) => {
        item.classList.toggle('d-none', Boolean(query) && !item.textContent.toLowerCase().includes(query));
    });
});

// The in-menu filter box is UI-only (no name attribute): stop its keyup/change
// events in the capture phase so they never reach the form's hx-trigger and
// cause pointless requests.
['keyup', 'change', 'search'].forEach((type) => {
    document.addEventListener(
        type,
        (event) => {
            if (event.target.matches?.('[data-filterbar-menufilter]')) event.stopPropagation();
        },
        true
    );
});
