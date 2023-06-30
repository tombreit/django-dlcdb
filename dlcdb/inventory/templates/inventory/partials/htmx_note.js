;(function () {
    // document.body.addEventListener("objectListChanged", function(evt){
    //     console.log("objectListChanged was triggered!");
    // })

    const modal = new bootstrap.Modal(document.getElementById("htmx-note-modal"))

    htmx.on("htmx:afterSwap", (e) => {
        // Response targeting #dialog => show the modal
        if (e.detail.target.id == "dialog") {
            modal.show()
        }
    })

    htmx.on("htmx:beforeSwap", (e) => {
        // Empty response targeting #dialog => hide the modal
        if (e.detail.target.id == "dialog" && !e.detail.xhr.response) {
            modal.hide()
            e.detail.shouldSwap = false
        }
    })

    // Remove dialog content after hiding
    htmx.on("hidden.bs.modal", () => {
        document.getElementById("dialog").innerHTML = ""
    })

    const toastElement = document.getElementById("toast")
    const toastBody = document.getElementById("toast-body")
    const toast = new bootstrap.Toast(toastElement, { delay: 2000 })

    htmx.on("showMessage", (e) => {
        toastBody.innerText = e.detail.value
        toast.show()
    })

})()
