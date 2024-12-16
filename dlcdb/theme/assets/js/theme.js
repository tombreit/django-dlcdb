import * as bootstrap from 'bootstrap'
import htmx from "htmx.org";
import TomSelect from 'tom-select';


// Keep track of initialized elements to prevent duplicates
const initializedElements = new WeakSet();

/**
 * Initializes TomSelect dropdowns for all elements with 'is-tom-select' class
 * TomSelect is a feature-rich select UI control with autocomplete and native-feeling keyboard navigation
 */
function initTomSelect(el) {
    if (initializedElements.has(el)) return;

    console.info("Initializing TomSelect for element:", el);
    let tomSelectConfig = {
        plugins: ['remove_button'],
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
