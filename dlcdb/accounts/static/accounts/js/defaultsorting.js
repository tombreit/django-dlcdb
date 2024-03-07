// SPDX-FileCopyrightText: 2024 Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

"use strict";

document.addEventListener("DOMContentLoaded", function(event) {
    console.log("[defaultsorting.js] Setting the initial sort options...")

    const initialUrlParam = ["is_active__exact", "1"];
    const url = new URL(window.location);

    if ( url.href.endsWith("/") ) {
        url.searchParams.set(...initialUrlParam);
        window.history.pushState({ path: url.href }, "", url.href);
        window.location = url.href;
    }

});
