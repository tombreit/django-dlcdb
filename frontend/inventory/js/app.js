import * as bootstrap from 'bootstrap';
import htmx from "htmx.org";
import $ from 'jquery';
import 'select2';
import TomSelect from 'tom-select';



(function () {
    // document.body.addEventListener("objectListChanged", function(evt){
    //     console.log("objectListChanged was triggered!");
    // })

    const noteModalElem = document.getElementById("htmx-note-modal");
    if (noteModalElem) {
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
    }

    const toastElement = document.getElementById("toast");
    if (toastElement) {
        const toastBody = document.getElementById("toast-body")
        const toast = new bootstrap.Toast(toastElement, { delay: 2000 })

        htmx.on("showMessage", (e) => {
            toastBody.innerText = e.detail.value
            toast.show()
        })
    }
    

   // Page-specific code for inventorize_room_detail only
   function inventorizeRoomDetail() {
        // Initialize TomSelect on the "device" field
        const deviceSelect = document.getElementById('id_device');
        if (deviceSelect) {
            new TomSelect(deviceSelect, {
                create: false,
                maxItems: 1,
                closeAfterSelect: true,
            });
        }

        // Filter table functionality
        const devicesTable = document.querySelector("#devices-table tbody");
        const devicesTableSearchInput = document.querySelector("#search-table-input");

        if(devicesTable && devicesTableSearchInput) {
            function filterDeviceTable(){
                const query = devicesTableSearchInput.value.toLowerCase();
                const rows = devicesTable.rows;

                for (const row of rows) {
                    let matchInRow = false;
                    for (const cell of row.cells) {
                        let cellContent = cell.textContent || cell.innerText;
                        cellContent = cellContent.toLowerCase();
                        if (cellContent.includes(query)) {
                            matchInRow = true;
                            break;
                        }
                    }
                    row.style.display = matchInRow ? "table-row" : "none";
                }
            }
            devicesTableSearchInput.addEventListener("keyup", filterDeviceTable);
        }
    }

    // Check if we're on the inventorize_room_detail page via a data attribute
    if (document.body.dataset.page === "inventorize-room-detail") {
        inventorizeRoomDetail();
    }

})();
