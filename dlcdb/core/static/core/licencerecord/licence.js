// SPDX-FileCopyrightText: 2024 Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

document.addEventListener("DOMContentLoaded", function(event) {

    b = document.getElementsByTagName("body")[0]

    if (b.matches(".model-licencerecord.change-list")) {
            let license_state_child_elem = document.getElementsByClassName("licence-state");

            for (item of license_state_child_elem) {
                let itemClasses = item.classList
                let parentTr = item.closest("tr")
                // using spread operator to unpack the individual classes:
                parentTr.classList.add(...itemClasses)
            }  
    }

});
