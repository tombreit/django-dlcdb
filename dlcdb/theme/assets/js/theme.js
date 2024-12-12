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

function initTomSelects() {
    // Initialize existing elements
    document.querySelectorAll('.is-tom-select').forEach(initTomSelect);

    // Observe DOM changes for dynamically added elements
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    if (node.matches('.is-tom-select')) {
                        initTomSelect(node);
                    }
                    node.querySelectorAll('.is-tom-select').forEach(initTomSelect);
                }
            });
        });
    });

    // Start observing the document body
    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });
}

// Initialize on DOMContentLoaded or immediately if the document is already ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTomSelects);
} else {
    initTomSelects();
}
