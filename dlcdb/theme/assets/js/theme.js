// SPDX-FileCopyrightText: 2025 Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

import * as bootstrap from 'bootstrap'
import htmx from "htmx.org";
import TomSelect from 'tom-select';

import './filterbar';

// Expose Bootstrap for slim per-app bundles (e.g. inventory) that need
// Modal/Toast programmatically without bundling Bootstrap a second time.
window.bootstrap = bootstrap;


// Keep track of initialized elements to prevent duplicates
const initializedElements = new WeakSet();

/**
 * Initializes TomSelect dropdowns for all elements with 'is-tom-select' class
 * TomSelect is a feature-rich select UI control with autocomplete and native-feeling keyboard navigation
 */
function initTomSelect(el) {
    if (initializedElements.has(el)) return;

    console.info("Initializing TomSelect for element:", el);
    // `remove_button` puts an "x" on each selected tag — the right affordance for
    // multi-selects. `clear_button` adds a single "clear all" control on the right,
    // which reads better on single selects. Opt in per element via
    // data-clear-button (e.g. the device form's FK selects); default stays
    // remove_button so existing consumers are unchanged.
    const plugin = el.dataset.clearButton !== undefined ? 'clear_button' : 'remove_button';
    let tomSelectConfig = {
        plugins: [plugin],
        create: false,
        hidePlaceholder: true,
        maxOptions: null,
        closeAfterSelect: true,
    };
    new TomSelect(el, tomSelectConfig);
    initializedElements.add(el);
}

function initTomSelects(rootElement) {
    rootElement.querySelectorAll('.is-tom-select').forEach(initTomSelect);
}

// Initialize existing elements on DOMContentLoaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        initTomSelects(document);
    });
} else {
    initTomSelects(document);
}

// Listen for HTMX afterSwap events
document.body.addEventListener('htmx:afterSwap', function(event) {
    initTomSelects(event.target);
});


/**
 * Bootstrap 5.3 color mode switcher (Light / Dark / Auto).
 * Adapted from https://getbootstrap.com/docs/5.3/customize/color-modes/#javascript
 * The initial data-bs-theme is set by an inline <head> script (see _base.html) to
 * avoid a flash of the wrong theme; this code only wires up the switcher in the
 * navbar's account menu and follows the OS preference while in "auto" mode.
 */
(() => {
    'use strict';

    const STORAGE_KEY = 'dlcdb-theme';
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');

    const getStoredTheme = () => localStorage.getItem(STORAGE_KEY);
    const setStoredTheme = (theme) => localStorage.setItem(STORAGE_KEY, theme);

    const getPreferredTheme = () => {
        const stored = getStoredTheme();
        if (stored) return stored;
        return prefersDark.matches ? 'dark' : 'light';
    };

    const setTheme = (theme) => {
        const resolved = theme === 'auto'
            ? (prefersDark.matches ? 'dark' : 'light')
            : theme;
        document.documentElement.setAttribute('data-bs-theme', resolved);
    };

    const showActiveTheme = (theme) => {
        document.querySelectorAll('[data-bs-theme-value]').forEach((btn) => {
            const isActive = btn.getAttribute('data-bs-theme-value') === theme;
            btn.classList.toggle('active', isActive);
            btn.setAttribute('aria-pressed', String(isActive));
        });
    };

    // Follow the OS preference, but only while the user hasn't pinned light/dark.
    prefersDark.addEventListener('change', () => {
        const stored = getStoredTheme();
        if (stored !== 'light' && stored !== 'dark') {
            setTheme(getPreferredTheme());
        }
    });

    const initThemeSwitcher = () => {
        // No stored choice means the page follows the OS, which is "auto".
        showActiveTheme(getStoredTheme() || 'auto');

        document.querySelectorAll('[data-bs-theme-value]').forEach((toggle) => {
            toggle.addEventListener('click', () => {
                const theme = toggle.getAttribute('data-bs-theme-value');
                setStoredTheme(theme);
                setTheme(theme);
                showActiveTheme(theme);
            });
        });
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initThemeSwitcher);
    } else {
        initThemeSwitcher();
    }
})();
