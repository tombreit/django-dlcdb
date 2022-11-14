document.addEventListener("DOMContentLoaded", function(event) {

    b = document.getElementsByTagName("body")[0]

    if (b.matches(".model-lentrecord.change-list")) {
            let lent_state_child_elem = document.getElementsByClassName("lent-state");

            for (item of lent_state_child_elem) {
                let itemClasses = item.classList
                let parentTr = item.closest("tr")
                // using spread operator to unpack the individual classes:
                parentTr.classList.add(...itemClasses)
            }  
    }

});
